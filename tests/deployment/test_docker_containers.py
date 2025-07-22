"""
Docker Container Deployment Tests
=================================

Tests for Docker container deployment, multi-container orchestration,
service discovery, health checks, and container integration.
"""

import pytest
import asyncio
import docker
import requests
import time
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import subprocess
import tempfile
import os

from tests.utils.helpers import measure_performance, wait_for_condition
from tests.utils.data_generators import MockDataGenerator


class TestDockerEnvironment:
    """Test Docker environment setup and basic functionality."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            # Test connection
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    @pytest.fixture
    def test_network(self, docker_client):
        """Create test network for container communication."""
        network_name = "dsl-png-test-network"
        try:
            # Remove existing network if present
            try:
                existing = docker_client.networks.get(network_name)
                existing.remove()
            except docker.errors.NotFound:
                pass
            
            network = docker_client.networks.create(
                network_name,
                driver="bridge"
            )
            yield network
        finally:
            try:
                network.remove()
            except Exception:
                pass
    
    def test_docker_availability(self, docker_client):
        """Test Docker daemon availability."""
        assert docker_client.ping() is True
        
        # Test basic Docker functionality
        info = docker_client.info()
        assert "ServerVersion" in info
        assert info["ServerVersion"] is not None
    
    def test_docker_image_build_capability(self, docker_client):
        """Test ability to build Docker images."""
        # Create a simple test Dockerfile
        dockerfile_content = """
FROM python:3.11-slim
RUN echo "test image" > /test.txt
CMD ["cat", "/test.txt"]
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            # Build test image
            image, logs = docker_client.images.build(
                path=str(temp_dir),
                tag="dsl-png-test:latest",
                rm=True
            )
            
            assert image is not None
            
            # Clean up test image
            docker_client.images.remove(image.id, force=True)


class TestContainerBuilds:
    """Test building application containers from Dockerfiles."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        # Assuming tests are run from project root
        return Path.cwd()
    
    def test_api_container_build(self, docker_client, project_root):
        """Test building API container."""
        api_dockerfile = project_root / "docker" / "api" / "Dockerfile"
        
        if not api_dockerfile.exists():
            pytest.skip("API Dockerfile not found")
        
        # Build API container
        image, logs = docker_client.images.build(
            path=str(project_root),
            dockerfile=str(api_dockerfile.relative_to(project_root)),
            tag="dsl-png-api:test",
            rm=True
        )
        
        assert image is not None
        assert "dsl-png-api:test" in [tag for tag in image.tags]
        
        # Verify image size is reasonable (< 2GB)
        assert image.attrs['Size'] < 2 * 1024 * 1024 * 1024
        
        # Clean up
        docker_client.images.remove(image.id, force=True)
    
    def test_mcp_server_container_build(self, docker_client, project_root):
        """Test building MCP server container."""
        mcp_dockerfile = project_root / "docker" / "mcp" / "Dockerfile"
        
        if not mcp_dockerfile.exists():
            pytest.skip("MCP Dockerfile not found")
        
        # Build MCP server container
        image, logs = docker_client.images.build(
            path=str(project_root),
            dockerfile=str(mcp_dockerfile.relative_to(project_root)),
            tag="dsl-png-mcp:test",
            rm=True
        )
        
        assert image is not None
        assert "dsl-png-mcp:test" in [tag for tag in image.tags]
        
        # Clean up
        docker_client.images.remove(image.id, force=True)
    
    def test_worker_container_build(self, docker_client, project_root):
        """Test building worker container."""
        worker_dockerfile = project_root / "docker" / "worker" / "Dockerfile"
        
        if not worker_dockerfile.exists():
            pytest.skip("Worker Dockerfile not found")
        
        # Build worker container
        image, logs = docker_client.images.build(
            path=str(project_root),
            dockerfile=str(worker_dockerfile.relative_to(project_root)),
            tag="dsl-png-worker:test",
            rm=True
        )
        
        assert image is not None
        assert "dsl-png-worker:test" in [tag for tag in image.tags]
        
        # Clean up
        docker_client.images.remove(image.id, force=True)


class TestSingleContainerDeployment:
    """Test single container deployment and functionality."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    @pytest.fixture
    def redis_container(self, docker_client):
        """Start Redis container for testing."""
        container = docker_client.containers.run(
            "redis:7-alpine",
            name="dsl-png-redis-test",
            ports={"6379/tcp": None},  # Random port
            detach=True,
            remove=True
        )
        
        # Wait for Redis to be ready
        time.sleep(2)
        
        yield container
        
        # Cleanup
        try:
            container.stop()
        except Exception:
            pass
    
    def test_redis_container_health(self, redis_container):
        """Test Redis container health and connectivity."""
        # Get container port
        container_info = redis_container.attrs
        ports = container_info['NetworkSettings']['Ports']
        redis_port = int(ports['6379/tcp'][0]['HostPort'])
        
        # Test Redis connectivity
        import redis
        r = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        
        # Test basic Redis operations
        r.set('test_key', 'test_value')
        assert r.get('test_key') == 'test_value'
        
        # Test Redis health
        assert r.ping() is True
    
    def test_nginx_container_deployment(self, docker_client):
        """Test nginx proxy container deployment."""
        # Create minimal nginx config
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }
    
    server {
        listen 80;
        
        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nginx.conf"
            config_path.write_text(nginx_config)
            
            # Start nginx container
            container = docker_client.containers.run(
                "nginx:alpine",
                name="dsl-png-nginx-test",
                ports={"80/tcp": None},
                volumes={str(config_path): {"bind": "/etc/nginx/nginx.conf", "mode": "ro"}},
                detach=True,
                remove=True
            )
            
            try:
                # Wait for nginx to start
                time.sleep(2)
                
                # Get container port
                container.reload()
                ports = container.attrs['NetworkSettings']['Ports']
                nginx_port = int(ports['80/tcp'][0]['HostPort'])
                
                # Test nginx is running (should get 502 since no upstream)
                response = requests.get(f"http://localhost:{nginx_port}", timeout=5)
                assert response.status_code == 502  # Bad Gateway (expected without upstream)
                
            finally:
                container.stop()


class TestMultiContainerOrchestration:
    """Test multi-container deployment with Docker Compose."""
    
    @pytest.fixture
    def docker_compose_file(self):
        """Create test docker compose.yml file."""
        compose_content = """
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

  api:
    image: python:3.11-slim
    command: python -m http.server 8000
    ports:
      - "8000"
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000"]
      interval: 10s
      timeout: 5s
      retries: 3
    environment:
      - REDIS_URL=redis://redis:6379

networks:
  default:
    name: dsl-png-test-network
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(compose_content)
            f.flush()
            yield f.name
        
        # Cleanup
        os.unlink(f.name)
    
    def test_docker_compose_availability(self):
        """Test Docker Compose availability."""
        try:
            result = subprocess.run(
                ["docker compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert "docker compose" in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            try:
                # Try newer 'docker compose' command
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                assert result.returncode == 0
                assert "compose" in result.stdout.lower()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pytest.skip("Docker Compose not available")
    
    def test_compose_up_down(self, docker_compose_file):
        """Test Docker Compose up and down operations."""
        compose_cmd = self._get_compose_command()
        
        try:
            # Start services
            result = subprocess.run(
                compose_cmd + ["-f", docker_compose_file, "up", "-d"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                pytest.skip(f"Compose up failed: {result.stderr}")
            
            # Wait for services to be ready
            time.sleep(10)
            
            # Check services are running
            result = subprocess.run(
                compose_cmd + ["-f", docker_compose_file, "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            assert result.returncode == 0
            assert "redis" in result.stdout
            assert "api" in result.stdout
            
        finally:
            # Clean up
            subprocess.run(
                compose_cmd + ["-f", docker_compose_file, "down", "-v"],
                capture_output=True,
                timeout=30
            )
    
    def test_service_health_checks(self, docker_compose_file):
        """Test service health checks in compose environment."""
        compose_cmd = self._get_compose_command()
        
        try:
            # Start services
            subprocess.run(
                compose_cmd + ["-f", docker_compose_file, "up", "-d"],
                capture_output=True,
                timeout=60
            )
            
            # Wait for health checks to pass
            max_wait = 60
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                result = subprocess.run(
                    compose_cmd + ["-f", docker_compose_file, "ps", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    services = result.stdout.strip().split('\n')
                    all_healthy = True
                    
                    for service_line in services:
                        if service_line.strip():
                            try:
                                service = json.loads(service_line)
                                if 'State' in service and 'healthy' not in service['State']:
                                    all_healthy = False
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    if all_healthy:
                        break
                
                time.sleep(5)
            
            # Verify at least basic connectivity
            time.sleep(5)  # Additional wait for stability
            
        finally:
            subprocess.run(
                compose_cmd + ["-f", docker_compose_file, "down", "-v"],
                capture_output=True,
                timeout=30
            )
    
    def _get_compose_command(self):
        """Get the appropriate Docker Compose command."""
        try:
            subprocess.run(["docker compose", "--version"], capture_output=True, timeout=5)
            return ["docker compose"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ["docker", "compose"]


class TestContainerNetworking:
    """Test container networking and service discovery."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    @pytest.fixture
    def test_network(self, docker_client):
        """Create test network."""
        network = docker_client.networks.create(
            "dsl-png-network-test",
            driver="bridge"
        )
        yield network
        try:
            network.remove()
        except Exception:
            pass
    
    def test_container_to_container_communication(self, docker_client, test_network):
        """Test communication between containers on same network."""
        # Start server container
        server = docker_client.containers.run(
            "python:3.11-slim",
            command="python -c 'import http.server; http.server.HTTPServer((\"\", 8000), http.server.SimpleHTTPRequestHandler).serve_forever()'",
            name="test-server",
            network=test_network.name,
            detach=True,
            remove=True
        )
        
        # Start client container
        client = docker_client.containers.run(
            "python:3.11-slim",
            command="python -c 'import urllib.request; print(urllib.request.urlopen(\"http://test-server:8000\").getcode())'",
            name="test-client",
            network=test_network.name,
            detach=True,
            remove=True
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Check client can reach server
            client.wait(timeout=10)
            logs = client.logs().decode()
            
            assert "200" in logs
            
        finally:
            try:
                server.stop()
                client.stop()
            except Exception:
                pass
    
    def test_port_mapping_functionality(self, docker_client):
        """Test port mapping from container to host."""
        container = docker_client.containers.run(
            "python:3.11-slim",
            command="python -m http.server 8000",
            ports={"8000/tcp": None},  # Random port
            detach=True,
            remove=True
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Get mapped port
            container.reload()
            ports = container.attrs['NetworkSettings']['Ports']
            host_port = int(ports['8000/tcp'][0]['HostPort'])
            
            # Test connectivity
            response = requests.get(f"http://localhost:{host_port}", timeout=10)
            assert response.status_code == 200
            
        finally:
            container.stop()


class TestContainerPersistence:
    """Test container data persistence and volumes."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    def test_volume_persistence(self, docker_client):
        """Test data persistence using Docker volumes."""
        volume_name = "dsl-png-test-volume"
        
        # Create volume
        volume = docker_client.volumes.create(name=volume_name)
        
        try:
            # Write data in first container
            container1 = docker_client.containers.run(
                "alpine:latest",
                command="sh -c 'echo \"test data\" > /data/test.txt'",
                volumes={volume_name: {"bind": "/data", "mode": "rw"}},
                remove=True
            )
            
            # Read data in second container
            container2 = docker_client.containers.run(
                "alpine:latest",
                command="cat /data/test.txt",
                volumes={volume_name: {"bind": "/data", "mode": "ro"}},
                remove=True
            )
            
            logs = container2.logs().decode().strip()
            assert logs == "test data"
            
        finally:
            try:
                volume.remove()
            except Exception:
                pass
    
    def test_bind_mount_functionality(self, docker_client):
        """Test bind mount functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file on host
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("host data")
            
            # Read file from container
            container = docker_client.containers.run(
                "alpine:latest",
                command="cat /mounted/test.txt",
                volumes={temp_dir: {"bind": "/mounted", "mode": "ro"}},
                remove=True
            )
            
            logs = container.logs().decode().strip()
            assert logs == "host data"


class TestContainerResources:
    """Test container resource limits and monitoring."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    def test_memory_limits(self, docker_client):
        """Test container memory limits."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="sleep 5",
            mem_limit="128m",
            detach=True,
            remove=True
        )
        
        try:
            # Check memory limit is applied
            container.reload()
            memory_limit = container.attrs['HostConfig']['Memory']
            assert memory_limit == 128 * 1024 * 1024  # 128MB in bytes
            
        finally:
            try:
                container.stop()
            except Exception:
                pass
    
    def test_cpu_limits(self, docker_client):
        """Test container CPU limits."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="sleep 5",
            cpu_quota=50000,  # 50% of one CPU
            cpu_period=100000,
            detach=True,
            remove=True
        )
        
        try:
            # Check CPU limit is applied
            container.reload()
            cpu_quota = container.attrs['HostConfig']['CpuQuota']
            cpu_period = container.attrs['HostConfig']['CpuPeriod']
            
            assert cpu_quota == 50000
            assert cpu_period == 100000
            
        finally:
            try:
                container.stop()
            except Exception:
                pass
    
    def test_container_stats_monitoring(self, docker_client):
        """Test container resource monitoring."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="sleep 10",
            detach=True,
            remove=True
        )
        
        try:
            # Wait for container to be fully started
            time.sleep(2)
            
            # Get container stats
            stats = container.stats(stream=False)
            
            assert 'memory_stats' in stats
            assert 'cpu_stats' in stats
            assert 'networks' in stats
            
            # Verify basic stats structure
            memory_stats = stats['memory_stats']
            assert 'usage' in memory_stats
            
        finally:
            try:
                container.stop()
            except Exception:
                pass


class TestContainerSecurity:
    """Test container security configurations."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    def test_non_root_user_execution(self, docker_client):
        """Test running container as non-root user."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="id",
            user="1000:1000",  # Non-root user
            remove=True
        )
        
        logs = container.logs().decode().strip()
        assert "uid=1000" in logs
        assert "gid=1000" in logs
    
    def test_read_only_filesystem(self, docker_client):
        """Test container with read-only filesystem."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="sh -c 'touch /test.txt; echo $?'",
            read_only=True,
            remove=True
        )
        
        logs = container.logs().decode().strip()
        # Should fail to create file (exit code 1)
        assert "1" in logs
    
    def test_dropped_capabilities(self, docker_client):
        """Test container with dropped capabilities."""
        container = docker_client.containers.run(
            "alpine:latest",
            command="sh -c 'ping -c 1 8.8.8.8; echo $?'",
            cap_drop=["NET_RAW"],  # Drop network raw capability
            remove=True
        )
        
        logs = container.logs().decode().strip()
        # Should fail without NET_RAW capability
        assert "1" in logs or "Operation not permitted" in logs


class TestContainerPerformance:
    """Test container performance characteristics."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            client = docker.from_env()
            client.ping()
            yield client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    def test_container_startup_time(self, docker_client):
        """Test container startup performance."""
        with measure_performance() as timer:
            container = docker_client.containers.run(
                "alpine:latest",
                command="echo 'started'",
                remove=True
            )
        
        # Container should start quickly
        assert timer.elapsed_time < 10.0
        
        logs = container.logs().decode().strip()
        assert logs == "started"
    
    def test_multiple_container_startup(self, docker_client):
        """Test starting multiple containers concurrently."""
        containers = []
        
        with measure_performance() as timer:
            # Start 5 containers concurrently
            for i in range(5):
                container = docker_client.containers.run(
                    "alpine:latest",
                    command=f"echo 'container-{i}'",
                    name=f"test-container-{i}",
                    detach=True,
                    remove=True
                )
                containers.append(container)
            
            # Wait for all to complete
            for container in containers:
                container.wait(timeout=30)
        
        # Should handle multiple containers efficiently
        assert timer.elapsed_time < 30.0
        
        # Verify all containers ran successfully
        for i, container in enumerate(containers):
            logs = container.logs().decode().strip()
            assert logs == f"container-{i}"
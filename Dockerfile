FROM node:20-slim

# Only install Node dependencies — no Chromium needed
WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

CMD ["node", "server.js"]

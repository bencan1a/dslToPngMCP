import express from "express";
import { renderDSLtoHTML } from "./renderHtml.js";
import puppeteer from "puppeteer";

const app = express();
app.use(express.json());

app.post("/render", async (req, res) => {
  const { width = 800, height = 600, elements = [], css = "" } = req.body;

  const html = renderDSLtoHTML({ width, height, elements, css });

  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  await page.setViewport({ width, height });

  await page.setContent(html, { waitUntil: "domcontentloaded" });

  const screenshot = await page.screenshot({ type: "png" });
  await browser.close();

  const base64 = `data:image/png;base64,${screenshot.toString("base64")}`;
  res.json({ image_base64: base64 });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Puppeteer MCP running on port ${PORT}`));

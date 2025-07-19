import express from "express";
import puppeteer from "puppeteer";
import { renderDSLtoHTML } from "./renderHtml.js";

const BROWSERLESS_ENDPOINT = process.env.BROWSERLESS_ENDPOINT || "ws://localhost:3000";
const app = express();
app.use(express.json());

app.post("/render", async (req, res) => {
  const { width = 800, height = 600, elements = [], css = "" } = req.body;

  const html = renderDSLtoHTML({ width, height, elements, css });

  const browser = await puppeteer.connect({
    browserWSEndpoint: BROWSERLESS_ENDPOINT
  });

  const page = await browser.newPage();
  await page.setViewport({ width, height });
  await page.setContent(html, { waitUntil: "domcontentloaded" });

  const screenshot = await page.screenshot({ type: "png" });
  await page.close(); // Avoid memory leaks

  const base64 = `data:image/png;base64,${screenshot.toString("base64")}`;
  res.json({ image_base64: base64 });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Render server running on port ${PORT}`));

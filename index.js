import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get("/ping", (req, res) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

app.post("/send-command", (req, res) => {
  const { command } = req.body;
  if (!command) {
    return res.status(400).json({ status: "error", message: "Aucune commande reçue" });
  }
  console.log("Commande reçue :", command);
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.json({ status: "success", command });
});

app.post("/relay-from-chatgpt", async (req, res) => {
  const { message } = req.body;
  if (!message) {
    return res.status(400).json({ status: "error", message: "Aucun message reçu" });
  }
  console.log("Message reçu depuis ChatGPT :", message);
  try {
    const response = await fetch(`${process.env.BRIDGE_URL || "https://golix-bridge.onrender.com"}/send-command`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ command: message })
    });
    const data = await response.json();
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "relayed", bridgeResponse: data });
  } catch (error) {
    res.status(500).json({ status: "error", message: "Impossible de relayer" });
  }
});

app.listen(PORT, () => {
  console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

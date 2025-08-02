// index.js - Golix Bridge UTF-8 + Liaison directe
import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// =========================
//  ROUTES API
// =========================

// Vérification du Bridge
app.get("/ping", (req, res) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// Réception commande manuelle
app.post("/send-command", (req, res) => {
  const { command } = req.body;

  if (!command) {
    return res.status(400).json({ status: "error", message: "Aucune commande reçue" });
  }

  console.log("Commande reçue :", command);

  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.json({ status: "success", command });
});

// =========================
//  LIAISON CHATGPT → BRIDGE
// =========================
app.post("/relay-from-chatgpt", async (req, res) => {
  const { message } = req.body;

  if (!message) {
    return res.status(400).json({ status: "error", message: "Aucun message reçu de ChatGPT" });
  }

  console.log("Message reçu depuis ChatGPT :", message);

  // Relais automatique vers /send-command
  try {
    const response = await fetch(`https://golix-bridge.onrender.com/send-command`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ command: message })
    });

    const data = await response.json();
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "relayed", bridgeResponse: data });

  } catch (error) {
    console.error("Erreur liaison ChatGPT → Bridge :", error);
    res.status(500).json({ status: "error", message: "Impossible de relayer la commande" });
  }
});

// =========================
//  LANCEMENT SERVEUR
// =========================
app.listen(PORT, () => {
  console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

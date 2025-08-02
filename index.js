// index.js - Golix Bridge complet et compatible Windows PowerShell
import express from "express";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware pour lire le JSON et les formulaires
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Route de test
app.get("/ping", (req, res) => {
  res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// Route pour recevoir une commande
app.post("/send-command", (req, res) => {
  const { command } = req.body;

  if (!command) {
    return res.status(400).json({ status: "error", message: "Aucune commande reçue" });
  }

  console.log("Commande reçue :", command);
  res.json({ status: "success", command });
});

// Lancement du serveur
app.listen(PORT, () => {
  console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

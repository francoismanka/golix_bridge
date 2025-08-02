// index.js - Golix Bridge complet
import express from "express";
import bodyParser from "body-parser";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(bodyParser.json());

// Route de test
app.get("/ping", (req, res) => {
  res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// Route pour recevoir une commande
app.post("/send-command", (req, res) => {
  const { command } = req.body;
  console.log("Commande reçue :", command);
  res.json({ status: "success", command });
});

app.listen(PORT, () => {
  console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

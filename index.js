import admin from "firebase-admin";
import express from "express";
import bodyParser from "body-parser";
import cors from "cors";

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});

const db = admin.database();

const app = express();
app.use(cors());
app.use(bodyParser.json());

app.get("/", (req, res) => {
  res.json({ status: "GOLIX Bridge en ligne" });
});

app.post("/send-command", async (req, res) => {
  try {
    const cmd = req.body.command;
    if (!cmd) {
      return res.status(400).json({ error: "Aucune commande fournie" });
    }

    console.log("[GOLIX-BRIDGE] Commande reçue :", cmd);

    await db.ref("chat_commands/latest").set({
      text: cmd,
      timestamp: Date.now()
    });

    console.log("[GOLIX-BRIDGE] Commande envoyée à Firebase !");
    res.json({ success: true });
  } catch (err) {
    console.error("[GOLIX-BRIDGE] Erreur :", err);
    res.status(500).json({ error: "Impossible d'envoyer la commande" });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[GOLIX-BRIDGE] Serveur en ligne sur le port ${PORT}`);
});

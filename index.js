// index.js - Golix Bridge avec moteur d'exécution des commandes
import express from "express";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// =========================
// Route de test
// =========================
app.get("/ping", (req, res) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// =========================
// Réception commande manuelle
// =========================
app.post("/send-command", (req, res) => {
    const { command } = req.body;
    if (!command) {
        return res.status(400).json({ status: "error", message: "Aucune commande reçue" });
    }

    console.log("📥 Commande reçue :", command);

    // Exécuter la commande
    executeGolixCommand(command);

    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "success", command });
});

// =========================
// Liaison ChatGPT → Bridge
// =========================
app.post("/relay-from-chatgpt", async (req, res) => {
    const { message } = req.body;
    if (!message) {
        return res.status(400).json({ status: "error", message: "Aucun message reçu de ChatGPT" });
    }

    console.log("💬 Message reçu depuis ChatGPT :", message);

    // Transmettre au moteur de commande
    executeGolixCommand(message);

    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "relayed", message });
});

// =========================
// Moteur de commandes Golix
// =========================
function executeGolixCommand(cmd) {
    switch (cmd.toLowerCase()) {
        case "démarre résilience & redondance":
            console.log("🛡 Activation du mode Résilience & Redondance…");
            // Ici, mets le code Golix réel pour activer ce mode
            break;
        case "analyse marché":
            console.log("📊 Analyse en cours des marchés…");
            // Ici, mets le code Golix d’analyse des marchés
            break;
        case "sécurité maximale":
            console.log("🔐 Passage en sécurité maximale…");
            // Ici, mets le code Golix pour activer le mode sécurité max
            break;
        default:
            console.log("ℹ Commande Golix inconnue :", cmd);
    }
}

// =========================
// Lancement serveur
// =========================
app.listen(PORT, () => {
    console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

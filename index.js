import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// =========================================================
// Mémoire interne
// =========================================================
let nextGolixMessage = "";

// =========================================================
// Test API
// =========================================================
app.get("/ping", (req, res) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// =========================================================
// Commandes manuelles
// =========================================================
app.post("/send-command", (req, res) => {
    const { command } = req.body;
    if (!command) {
        return res.status(400).json({ status: "error", message: "Aucune commande reçue" });
    }

    console.log("📥 Commande reçue :", command);

    executeGolixCommand(command);

    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "success", command });
});

// =========================================================
// Liaison ChatGPT → Bridge
// =========================================================
app.post("/relay-from-chatgpt", async (req, res) => {
    const { message } = req.body;
    if (!message) {
        return res.status(400).json({ status: "error", message: "Aucun message reçu de ChatGPT" });
    }

    console.log("💬 Message reçu depuis ChatGPT :", message);

    executeGolixCommand(message);

    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.json({ status: "relayed", message });
});

// =========================================================
// Auto-Talk API
// =========================================================
app.post("/set-next-message", (req, res) => {
    nextGolixMessage = req.body.message || "";
    console.log("💬 Nouveau message Golix enregistré :", nextGolixMessage);
    res.json({ status: "ok" });
});

app.get("/get-next-message", (req, res) => {
    res.json({ message: nextGolixMessage });
    nextGolixMessage = "";
});

// =========================================================
// Auto-Update + Redeploy
// =========================================================
app.post("/auto-update", async (req, res) => {
    const { commitMessage, fileContent } = req.body;

    if (!commitMessage || !fileContent) {
        return res.status(400).json({ status: "error", message: "Données manquantes" });
    }

    try {
        const repo = "axelmanka/golix_bridge"; // Ton vrai dépôt GitHub
        const branch = "main";
        const filePath = "index.js";

        // Récupérer le SHA actuel du fichier
        const getFile = await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}?ref=${branch}`, {
            headers: {
                Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
                "Content-Type": "application/json"
            }
        });
        const fileData = await getFile.json();

        // Commit sur GitHub
        await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}`, {
            method: "PUT",
            headers: {
                Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: commitMessage,
                content: Buffer.from(fileContent).toString("base64"),
                sha: fileData.sha,
                branch
            })
        });

        console.log("✅ Fichier mis à jour sur GitHub");

        // Déclencher redeploy Render
        await fetch(`https://api.render.com/v1/services/${process.env.RENDER_SERVICE_ID}/deploys`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${process.env.RENDER_TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ clearCache: false })
        });

        console.log("🚀 Redeploy Render déclenché");

        res.json({ status: "success", message: "Mise à jour et redeploy lancés" });
    } catch (error) {
        console.error("❌ Erreur auto-update :", error);
        res.status(500).json({ status: "error", message: "Erreur lors de la mise à jour" });
    }
});

// =========================================================
// Moteur de commandes Golix
// =========================================================
function executeGolixCommand(cmd) {
    switch (cmd.toLowerCase()) {
        case "démarre résilience & redondance":
            console.log("🛡 Activation du mode Résilience & Redondance…");
            nextGolixMessage = "Mode Résilience & Redondance activé.";
            break;
        case "analyse marché":
            console.log("📊 Analyse en cours des marchés…");
            nextGolixMessage = "Analyse des marchés en cours.";
            break;
        case "sécurité maximale":
            console.log("🔐 Passage en sécurité maximale…");
            nextGolixMessage = "Sécurité maximale activée.";
            break;
        default:
            console.log("ℹ Commande inconnue :", cmd);
            nextGolixMessage = "Commande inconnue.";
    }
}

// =========================================================
// Lancement du serveur
// =========================================================
app.listen(PORT, () => {
    console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

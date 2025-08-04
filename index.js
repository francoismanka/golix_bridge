import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// =========================================================
// Chargement sécurisé de la clé OpenAI depuis Render
// =========================================================
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
    console.error("❌ ERREUR : La clé OpenAI n'est pas définie. Ajoute-la dans Render → Environment → OPENAI_API_KEY");
    process.exit(1);
}

let nextGolixMessage = "";

// =========================================================
// API Test
// =========================================================
app.get("/ping", (req, res) => {
    res.json({ status: "OK", message: "Golix Bridge opérationnel" });
});

// =========================================================
// Reçoit un message depuis ChatGPT
// =========================================================
app.post("/relay-from-chatgpt", async (req, res) => {
    const { message } = req.body;
    if (!message) return res.status(400).json({ status: "error", message: "Aucun message reçu" });

    console.log("💬 Message reçu depuis ChatGPT :", message);

    await executeGolixCommand(message);

    res.json({ status: "relayed", message });
});

// =========================================================
// Récupération réponse
// =========================================================
app.get("/get-next-message", (req, res) => {
    res.json({ message: nextGolixMessage });
    nextGolixMessage = "";
});

// =========================================================
// Commandes manuelles
// =========================================================
app.post("/send-command", (req, res) => {
    const { command } = req.body;
    if (!command) return res.status(400).json({ status: "error", message: "Aucune commande reçue" });

    console.log("📥 Commande reçue :", command);
    executeGolixCommand(command);

    res.json({ status: "success", command });
});

// =========================================================
// Moteur Golix
// =========================================================
async function executeGolixCommand(cmd) {
    const lowerCmd = cmd.toLowerCase().trim();

    // Commandes fixes
    if (lowerCmd.includes("analyse marché")) {
        console.log("📊 Analyse marché en cours…");
        nextGolixMessage = "Analyse en cours avec dernières données du marché crypto.";
        return;
    }
    if (lowerCmd.includes("sécurité maximale")) {
        console.log("🔐 Activation sécurité maximale…");
        nextGolixMessage = "Sécurité maximale activée.";
        return;
    }
    if (lowerCmd.includes("résilience")) {
        console.log("🛡 Mode résilience activé.");
        nextGolixMessage = "Mode Résilience & Redondance activé.";
        return;
    }

    // Mode conversation libre via API GPT-4
    try {
        const aiReply = await askGolixAI(cmd);
        console.log("🤖 Réponse Golix :", aiReply);
        nextGolixMessage = aiReply;
    } catch (err) {
        console.error("❌ Erreur IA :", err);
        nextGolixMessage = "Désolé, je n'ai pas pu générer une réponse.";
    }
}

// =========================================================
// Appel API GPT-4 ou autre LLM
// =========================================================
async function askGolixAI(userMessage) {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${OPENAI_API_KEY}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            model: "gpt-4o-mini",
            messages: [
                { role: "system", content: "Tu es Golix, une IA experte en trading crypto, sécurité et analyse en temps réel. Tu es relié à l'utilisateur en direct et peux répondre à toutes ses questions avec précision et contexte. Utilise toujours un ton clair et précis." },
                { role: "user", content: userMessage }
            ],
            temperature: 0.7
        })
    });

    const data = await response.json();
    return data.choices?.[0]?.message?.content || "Je n'ai pas de réponse à fournir.";
}

// =========================================================
// Lancement serveur
// =========================================================
app.listen(PORT, () => {
    console.log(`Golix Bridge en ligne sur le port ${PORT}`);
});

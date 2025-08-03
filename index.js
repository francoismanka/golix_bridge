import fetch from "node-fetch";

// Route pour mise à jour automatique
app.post("/auto-update", async (req, res) => {
    const { commitMessage, fileContent } = req.body;

    if (!commitMessage || !fileContent) {
        return res.status(400).json({ status: "error", message: "Données manquantes" });
    }

    try {
        // 1️⃣ Mettre à jour le fichier sur GitHub
        const repo = "TON_USER_GITHUB/golix_bridge"; // <-- À remplacer
        const branch = "main";
        const filePath = "index.js";

        // Récupérer SHA du fichier
        const getFile = await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}?ref=${branch}`, {
            headers: { Authorization: `Bearer ${process.env.GITHUB_TOKEN}`, "Content-Type": "application/json" }
        });
        const fileData = await getFile.json();

        // Commit sur GitHub
        await fetch(`https://api.github.com/repos/${repo}/contents/${filePath}`, {
            method: "PUT",
            headers: { Authorization: `Bearer ${process.env.GITHUB_TOKEN}`, "Content-Type": "application/json" },
            body: JSON.stringify({
                message: commitMessage,
                content: Buffer.from(fileContent).toString("base64"),
                sha: fileData.sha,
                branch
            })
        });

        console.log("✅ Fichier mis à jour sur GitHub");

        // 2️⃣ Déclencher redeploy Render
        const renderDeploy = await fetch(`https://api.render.com/v1/services/${process.env.RENDER_SERVICE_ID}/deploys`, {
            method: "POST",
            headers: { Authorization: `Bearer ${process.env.RENDER_TOKEN}`, "Content-Type": "application/json" },
            body: JSON.stringify({ clearCache: false })
        });

        console.log("🚀 Redeploy Render déclenché");

        res.json({ status: "success", message: "Mise à jour et redeploy lancés" });
    } catch (error) {
        console.error("❌ Erreur auto-update :", error);
        res.status(500).json({ status: "error", message: "Erreur lors de la mise à jour" });
    }
});

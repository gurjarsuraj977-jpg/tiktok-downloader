const urlInput = document.getElementById("urlInput");
const downloadBtn = document.getElementById("downloadBtn");
const statusBox = document.getElementById("status");
const resultBox = document.getElementById("result");
const downloadLink = document.getElementById("downloadLink");

downloadBtn.addEventListener("click", async () => {

    const url = urlInput.value.trim();

    resultBox.classList.add("hidden");
    downloadLink.removeAttribute("href");

    if (!url) {
        statusBox.textContent = "Paste a TikTok URL first.";
        return;
    }

    downloadBtn.disabled = true;
    downloadBtn.textContent = "Downloading...";
    statusBox.textContent = "Processing video...";

    try {

        const response = await fetch("/api/download", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                url: url
            })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            throw new Error(
                data.error || "Download failed."
            );
        }

        statusBox.textContent = "Video is ready.";

        downloadLink.href = data.download_url;
        downloadLink.download = data.filename;

        resultBox.classList.remove("hidden");

    } catch (error) {

        statusBox.textContent =
            error.message || "Something went wrong.";

    } finally {

        downloadBtn.disabled = false;
        downloadBtn.textContent = "Download";

    }

});

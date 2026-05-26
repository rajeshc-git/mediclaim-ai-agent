// Autonomous ReAct Agent HUD Controller

document.addEventListener("DOMContentLoaded", () => {
    // UI Selectors
    const promptForm = document.getElementById("prompt-form");
    const promptInput = document.getElementById("prompt-input");
    const sendBtn = document.getElementById("send-btn");
    const logScreen = document.getElementById("log-screen");
    const clearFeedBtn = document.getElementById("clear-feed-btn");

    // Sidebar Telemetry Selectors
    const hudProvider = document.getElementById("hud-provider");
    const hudModel = document.getElementById("hud-model");
    const hudMode = document.getElementById("hud-mode");
    const memoryCounter = document.getElementById("memory-counter");
    const memoryMeter = document.getElementById("memory-meter");
    const toolsContainer = document.getElementById("tools-container");

    // Header HUD Status
    const globalPulse = document.getElementById("global-pulse");
    const globalStatusText = document.getElementById("global-status-text");
    const systemClock = document.getElementById("system-clock");
    const footerStatusDetails = document.getElementById("footer-status-details");

    let eventSource = null;

    // 0. Theme Toggle Logic
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    const themeToggleIcon = document.getElementById("theme-toggle-icon");
    const themeToggleLabel = document.getElementById("theme-toggle-label");
    const htmlEl = document.documentElement;

    const DARK_ICON = "☀️";
    const LIGHT_ICON = "🌙";
    const DARK_LABEL = "LIGHT";  // button shows what theme you'll switch TO
    const LIGHT_LABEL = "DARK";

    function applyTheme(theme) {
        htmlEl.setAttribute("data-theme", theme);
        localStorage.setItem("ag-theme", theme);
        if (theme === "dark") {
            themeToggleIcon.textContent = DARK_ICON;
            themeToggleLabel.textContent = DARK_LABEL;
        } else {
            themeToggleIcon.textContent = LIGHT_ICON;
            themeToggleLabel.textContent = LIGHT_LABEL;
        }
    }

    // Restore saved preference or system default
    const savedTheme = localStorage.getItem("ag-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(savedTheme || (prefersDark ? "dark" : "light"));

    themeToggleBtn.addEventListener("click", () => {
        const current = htmlEl.getAttribute("data-theme");
        applyTheme(current === "dark" ? "light" : "dark");
    });

    // 0b. Mobile Sidebar — Dot Indicator
    const sidebarHud = document.getElementById("sidebar-hud");
    const sidebarDots = document.querySelectorAll(".sidebar-dot");
    const panels = sidebarHud ? sidebarHud.querySelectorAll(".hud-panel") : [];

    if (sidebarHud && sidebarDots.length && panels.length) {

        // --- Live dot tracking via IntersectionObserver ---
        const observerOptions = {
            root: sidebarHud,
            threshold: 0.55   // panel must be >55% visible to be "active"
        };

        const dotObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const idx = Array.from(panels).indexOf(entry.target);
                if (idx === -1) return;
                sidebarDots.forEach((d, i) => d.classList.toggle("active", i === idx));
            });
        }, observerOptions);

        panels.forEach(panel => dotObserver.observe(panel));

        // --- Clicking a dot scrolls to that panel ---
        sidebarDots.forEach((dot, i) => {
            dot.addEventListener("click", () => {
                panels[i].scrollIntoView({ behavior: "smooth", block: "nearest", inline: "start" });
            });
        });
    }

    // 1. Start Live HUD Clock
    function updateClock() {
        const now = new Date();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        systemClock.textContent = `${hrs}:${mins}:${secs}`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Fetch Initial Server Status
    async function loadServerStatus() {
        try {
            const res = await fetch("/api/status");
            if (res.ok) {
                const data = await res.json();

                // Update Sidebar
                hudProvider.textContent = data.provider.toUpperCase();
                hudModel.textContent = data.model.toUpperCase();
                hudMode.textContent = data.mode.toUpperCase();

                // Set appropriate glow coloring
                if (data.provider === "openai") {
                    hudProvider.className = "tel-val glow-cyan";
                } else if (data.provider === "gemini") {
                    hudProvider.className = "tel-val glow-blue";
                }

                if (data.mode.includes("Mock")) {
                    hudMode.className = "tel-val glow-orange";
                } else {
                    hudMode.className = "tel-val glow-green";
                }

                // Render Capability Tool Chips
                toolsContainer.innerHTML = "";
                data.tools.forEach(tool => {
                    const chip = document.createElement("span");
                    chip.className = "tool-chip";
                    chip.id = `tool-chip-${tool}`;
                    chip.textContent = tool;
                    toolsContainer.appendChild(chip);
                });

                footerStatusDetails.textContent = "CONNECTED // ONLINE";
            }
        } catch (e) {
            console.error("Failed to connect to backend telemetry server:", e);
            footerStatusDetails.textContent = "OFFLINE // CONNECTION LOST";
            footerStatusDetails.className = "glow-orange";
        }
    }
    loadServerStatus();

    // 3. Clear logs
    clearFeedBtn.addEventListener("click", () => {
        logScreen.innerHTML = `
            <div class="terminal-card welcome-card">
                <div class="card-tag system-tag">SYSTEM RESET</div>
                <p class="boot-text">Log terminal database cleared successfully.</p>
                <p class="boot-subtext">Awaiting target task parameter deploy...</p>
            </div>
        `;
    });

    // 4. Submit Chat Query via Server-Sent Events (SSE)
    promptForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const query = promptInput.value.trim();
        if (!query) return;

        // Reset and clear log screen for new run
        logScreen.innerHTML = "";
        appendJobStartCard(query);

        // Lock form inputs
        promptInput.disabled = true;
        sendBtn.disabled = true;
        promptInput.placeholder = "Agent is deployed. Processing reasoning streams...";

        // Set status to Active/Thinking
        setSystemStatus("processing");

        // Format parameters
        const url = `/api/chat?q=${encodeURIComponent(query)}`;

        // Open live streaming SSE Channel
        if (eventSource) eventSource.close();
        eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            const data = jsonParseSafe(event.data);
            if (!data) return;

            // Handle event payloads
            switch (data.type) {
                case "handshake":
                    // Handshake informs client which LLM provider is actively reasoning
                    hudProvider.textContent = data.provider.toUpperCase();
                    hudModel.textContent = data.model.toUpperCase();
                    hudMode.textContent = data.mode === "Live" ? "API CONNECTED" : "MOCK SANDBOX";
                    hudMode.className = data.mode === "Live" ? "tel-val glow-green" : "tel-val glow-orange";
                    break;

                case "step_start":
                    appendStepDivider(data.step);
                    break;

                case "thought":
                    appendThoughtCard(data.text);
                    break;

                case "tool_call":
                    highlightToolChip(data.tool, true);
                    appendActionCard(data.tool, data.args);
                    break;

                case "tool_observation":
                    highlightToolChip(data.tool, false);
                    appendObservationCard(data.tool, data.observation);
                    break;

                case "tool_error":
                    highlightToolChip(data.tool, false);
                    appendToolErrorCard(data.tool, data.error);
                    break;

                case "telemetry":
                    updateMemoryMeter(data.memory_size);
                    break;

                case "final_answer":
                    appendFinalAnswerCard(data.text);
                    closeStream();
                    break;

                case "error":
                    appendErrorCard(data.message);
                    closeStream();
                    break;
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE stream error:", err);
            appendErrorCard("Connection to streaming reasoning channel broke. Attempting local fail-safe recovery...");
            closeStream();
        };
    });

    // UI Rendering Helpers
    function setSystemStatus(status) {
        if (status === "processing") {
            globalPulse.className = "status-pulse active";
            globalStatusText.textContent = "AGENT ENGAGED";
            globalStatusText.style.color = "var(--neon-orange)";
            footerStatusDetails.textContent = "DEPLOYING WORKSPACE REASONER";
        } else {
            globalPulse.className = "status-pulse idle";
            globalStatusText.textContent = "SYSTEM STANDBY";
            globalStatusText.style.color = "var(--text-primary)";
            footerStatusDetails.textContent = "CONNECTED // ONLINE";
        }
    }

    async function closeStream() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        promptInput.disabled = false;
        sendBtn.disabled = false;
        promptInput.value = "";
        promptInput.placeholder = "Input target task parameters (e.g. Write a poem to poem.txt)...";
        setSystemStatus("idle");

        // Production-grade fallback: Query the backend directly for the newly generated Excel file
        // and inject the download button if it was missed or omitted during AI text streaming.
        try {
            // Delay slightly to ensure file writing has completely flushed to disk
            await new Promise(resolve => setTimeout(resolve, 500));

            const res = await fetch("/api/latest-audit");
            if (res.ok) {
                const data = await res.json();
                if (data.filename) {
                    // Check if a download button has already been rendered on the screen
                    const existingBtn = document.querySelector(".xlsx-download-btn");
                    if (!existingBtn) {
                        const answerCards = document.querySelectorAll(".answer-card");
                        if (answerCards.length > 0) {
                            const lastCard = answerCards[answerCards.length - 1];
                            const contentDiv = lastCard.querySelector(".ans-content");
                            if (contentDiv) {
                                const btnContainer = document.createElement("div");
                                btnContainer.className = "xlsx-download-btn-container";
                                btnContainer.style.marginTop = "15px";
                                btnContainer.innerHTML = `
                                    <div class="xlsx-download-btn-container">
                                        <a href="/claims_audit/${data.filename}" download="${data.filename}" class="xlsx-download-btn">
                                            <span class="xlsx-btn-icon">📊</span>
                                            <span>Download Excel Report (.xlsx)</span>
                                        </a>
                                    </div>
                                `;
                                contentDiv.appendChild(btnContainer);
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Failed to dynamically check generated audit files: ", e);
        }
    }

    function highlightToolChip(tool, isActive) {
        const chip = document.getElementById(`tool-chip-${tool}`);
        if (chip) {
            if (isActive) {
                chip.classList.add("active");
            } else {
                chip.classList.remove("active");
            }
        }
    }

    function updateMemoryMeter(size) {
        const percent = Math.min((size / 40) * 100, 100);
        memoryCounter.textContent = `${size} / 40 msgs`;
        memoryMeter.style.width = `${percent}%`;
    }

    // Card Append Creators
    function appendJobStartCard(query) {
        const card = document.createElement("div");
        card.className = "terminal-card welcome-card border-glow";
        card.innerHTML = `
            <div class="card-tag system-tag">JOB INITIATED</div>
            <p class="boot-text">Target parameters deployed:</p>
            <p class="boot-subtext" style="font-family: 'Fira Code', monospace; color: var(--neon-cyan); margin-top: 8px;">&gt; ${query}</p>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendStepDivider(step) {
        const divider = document.createElement("div");
        divider.style.textAlign = "center";
        divider.style.margin = "10px 0";
        divider.innerHTML = `
            <p style="font-family: 'Fira Code', monospace; font-size: 10px; color: var(--border-color); letter-spacing: 2px;">
                ───────────── REASONING TURN #${step} ─────────────
            </p>
        `;
        logScreen.appendChild(divider);
        scrollTerminal();
    }

    function appendThoughtCard(text) {
        const card = document.createElement("div");
        card.className = "terminal-card thought-card";
        card.innerHTML = `
            <div class="card-tag thought-tag">THOUGHT</div>
            <p>${text}</p>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendActionCard(tool, args) {
        const card = document.createElement("div");
        card.className = "terminal-card action-card";
        card.innerHTML = `
            <div class="card-tag action-tag">ACTION</div>
            <p style="font-size: 13px; font-weight: 600;">Invoking capability tool: <span style="color: var(--neon-cyan);">${tool}</span></p>
            <pre>Arguments: ${JSON.stringify(args, null, 2)}</pre>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendObservationCard(tool, result) {
        const card = document.createElement("div");
        card.className = "terminal-card obs-card";
        card.innerHTML = `
            <div class="card-tag obs-tag">OBSERVATION FROM '${tool.toUpperCase()}'</div>
            <pre>${escapeHtml(result)}</pre>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendToolErrorCard(tool, error) {
        const card = document.createElement("div");
        card.className = "terminal-card tool-error-card";
        card.innerHTML = `
            <div class="card-tag error-tag">TOOL FAILURE</div>
            <p>Tool '${tool}' execution aborted: ${error}</p>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendFinalAnswerCard(text) {
        const card = document.createElement("div");
        card.className = "terminal-card answer-card";

        // Parse basic markdown formats for pretty display
        const parsedText = formatMarkdownSafe(text);

        card.innerHTML = `
            <div class="card-tag answer-tag">FINAL ANSWER</div>
            <div class="ans-content">${parsedText}</div>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function appendErrorCard(msg) {
        const card = document.createElement("div");
        card.className = "terminal-card tool-error-card";
        card.innerHTML = `
            <div class="card-tag error-tag">SYSTEM ERROR</div>
            <p>${msg}</p>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }

    function scrollTerminal() {
        logScreen.scrollTop = logScreen.scrollHeight;
    }

    // Helper Utility Methods
    function jsonParseSafe(str) {
        try {
            return JSON.parse(str);
        } catch (e) {
            return null;
        }
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function parseMarkdownTables(text) {
        const lines = text.split('\n');
        let inTable = false;
        let tableRows = [];
        let newLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('|') && line.endsWith('|')) {
                if (!inTable) {
                    inTable = true;
                    tableRows = [];
                }
                tableRows.push(line);
            } else {
                if (inTable) {
                    const htmlTable = convertMarkdownTableToHtml(tableRows);
                    newLines.push(htmlTable);
                    inTable = false;
                }
                newLines.push(lines[i]);
            }
        }
        if (inTable) {
            const htmlTable = convertMarkdownTableToHtml(tableRows);
            newLines.push(htmlTable);
        }
        return newLines.join('\n');
    }

    function convertMarkdownTableToHtml(rows) {
        if (rows.length < 1) return "";

        // Extract headers
        const headerRow = rows[0];
        const headers = headerRow.split('|')
            .map(c => c.trim())
            .filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);

        let startIndex = 1;
        if (rows.length > 1 && rows[1].includes('-')) {
            startIndex = 2; // skip the divider row
        }

        let html = '<div class="table-container"><table class="premium-hud-table"><thead><tr>';

        headers.forEach(h => {
            html += `<th>${h}</th>`;
        });
        html += '</tr></thead><tbody>';

        for (let i = startIndex; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.split('|')
                .map(c => c.trim())
                .filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);

            html += '<tr>';
            cells.forEach(c => {
                // Keep strong text or simple styling in cells
                let cellVal = c
                    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
                    .replace(/`([^`]+)`/g, "<code>$1</code>");
                html += `<td>${cellVal}</td>`;
            });

            if (cells.length < headers.length) {
                for (let j = cells.length; j < headers.length; j++) {
                    html += '<td></td>';
                }
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        return html;
    }

    function formatMarkdownSafe(text) {
        let processed = text;

        // Find any xlsx file reference, e.g., claim_ICR33504.xlsx or ICR33504_Audit_Report.xlsx
        let xlsxFilename = null;
        const xlsxMatch = /[A-Za-z0-9_\-]+\.xlsx/i.exec(processed);
        if (xlsxMatch) {
            xlsxFilename = xlsxMatch[0];
        }

        // Remove lines containing "[JSON Report]" or the word "JSON" in a list
        processed = processed.replace(/^.*\[JSON Report\].*$/gim, "");
        processed = processed.replace(/^.*JSON.*$/gim, "");

        // Remove lines containing "[Excel Spreadsheet]" or "Excel" in a list (since we are making a custom button)
        processed = processed.replace(/^.*\[Excel Spreadsheet\].*$/gim, "");
        processed = processed.replace(/^.*Excel.*$/gim, "");

        // Remove common intro phrases for file lists to make it look clean
        processed = processed.replace(/Detailed audit reports are available in the following formats:?/gi, "");
        processed = processed.replace(/Audit reports saved to workspace paths:?/gi, "");
        processed = processed.replace(/Audit reports saved to:?/gi, "");
        processed = processed.replace(/The detailed audit reports are available below:?/gi, "");

        // Remove any leftover empty bullet points or double breaks
        processed = processed.replace(/^\s*[-*●]\s*$/gim, "");

        // Trim double/triple newlines to keep it neat
        processed = processed.replace(/\n{3,}/g, "\n\n");

        // Safe escaping first
        let html = escapeHtml(processed);

        // Parse markdown tables securely after HTML escaping
        html = parseMarkdownTables(html);

        // Convert markdown code blocks
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code>${code}</code></pre>`;
        });

        // Convert single line code highlights
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

        // Convert Bold highlights
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        // Convert Headings
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Convert Bullet List items cleanly
        html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<div class="bullet-item"><span class="bullet-dot">●</span> <span>$1</span></div>');

        // Convert newlines to breaks (ignoring pre tags)
        html = html.split("<pre>").map((chunk, idx) => {
            if (idx === 0) return chunk.replace(/\n/g, "<br>");
            const subChunks = chunk.split("</pre>");
            subChunks[0] = "<pre>" + subChunks[0] + "</pre>";
            if (subChunks[1]) {
                subChunks[1] = subChunks[1].replace(/\n/g, "<br>");
            }
            return subChunks.join("");
        }).join("");

        // Append the beautiful glassmorphic download button at the bottom if we found an XLSX file
        if (xlsxFilename) {
            html += `
                <div class="xlsx-download-btn-container">
                    <a href="/claims_audit/${xlsxFilename}" download="${xlsxFilename}" class="xlsx-download-btn">
                        <span class="xlsx-btn-icon">📊</span>
                        <span>Download Excel Report (.xlsx)</span>
                    </a>
                </div>
            `;
        }

        return html;
    }

    // 5. Interactive Batch Ingestion Depot
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const ingestCategory = document.getElementById("ingest-category");
    const uploadStatus = document.getElementById("upload-status");

    if (dropZone && fileInput) {
        // Click drop-zone to trigger hidden file input
        dropZone.addEventListener("click", () => {
            fileInput.click();
        });

        // Handle file selection via explorer click
        fileInput.addEventListener("change", (e) => {
            if (fileInput.files.length > 0) {
                handleFileUpload(fileInput.files);
            }
        });

        // Drag-and-drop styles toggle
        ["dragenter", "dragover"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add("drag-over");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove("drag-over");
            }, false);
        });

        // Handle dropped files
        dropZone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleFileUpload(files);
            }
        });
    }

    async function handleFileUpload(files) {
        if (!uploadStatus) return;

        const category = ingestCategory ? ingestCategory.value : "patient";

        uploadStatus.textContent = "TRANSMITTING DATA PACKETS...";
        uploadStatus.className = "upload-status transmitting";

        const formData = new FormData();
        formData.append("category", category);
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        try {
            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                uploadStatus.textContent = "TRANSMISSION COMPLETE";
                uploadStatus.className = "upload-status success";

                // Print completion notification in Terminal Monitor
                appendUploadCompletedCard(result.files, result.category, result.directory);

                // Clear input
                fileInput.value = "";

                // Reset status to standby after 4 seconds
                setTimeout(() => {
                    if (uploadStatus.className.includes("success")) {
                        uploadStatus.textContent = "READY FOR DATA PACKETS";
                        uploadStatus.className = "upload-status";
                    }
                }, 4000);
            } else {
                const errText = await response.text();
                throw new Error(errText || "Server error");
            }
        } catch (err) {
            console.error("Upload failed:", err);
            uploadStatus.textContent = "TRANSMISSION FAILED";
            uploadStatus.className = "upload-status error";
        }
    }

    function appendUploadCompletedCard(uploadedFiles, category, directory) {
        const card = document.createElement("div");
        card.className = "terminal-card welcome-card border-glow";
        card.style.borderColor = "var(--neon-green)";
        card.style.background = "rgba(0, 255, 102, 0.05)";

        const typeLabel = category === "patient" ? "PATIENT DATA INGESTED" : "POLICY LAWS INGESTED";

        let fileListHTML = "";
        uploadedFiles.forEach(file => {
            const sizeKB = (file.size / 1024).toFixed(1);
            fileListHTML += `<p style="font-family: 'Fira Code', monospace; color: var(--neon-green); margin: 4px 0 0 12px; font-size: 12px;">✔ ${file.filename} (${sizeKB} KB)</p>`;
        });

        card.innerHTML = `
            <div class="card-tag system-tag" style="background: var(--neon-green); color: black;">${typeLabel}</div>
            <p class="boot-text" style="color: var(--text-primary); font-size: 13.5px;">Ingestion successful! Saved to local folder <code>${directory}/</code></p>
            <div style="margin-top: 8px; border-top: 1px dashed rgba(0,255,102,0.2); padding-top: 6px;">
                ${fileListHTML}
            </div>
            <p class="boot-subtext" style="margin-top: 8px;">Workspace is fully primed. You can now prompt the auditor to analyze these new resources.</p>
        `;
        logScreen.appendChild(card);
        scrollTerminal();
    }
});

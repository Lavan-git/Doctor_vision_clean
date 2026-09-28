/* =========================================================
   Doctor Vision AI Chatbot
   Requires:
   <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
   <script src="/static/chatbot.js"></script>
   ========================================================= */

(function () {
    const chatbot = document.getElementById("doctorVisionChatbot");
    if (!chatbot) return;

    const launcher = document.getElementById("dvChatbotLauncher");
    const closeButton = document.getElementById("dvChatbotClose");
    const chatWindow = document.getElementById("dvChatbotWindow");
    const messages = document.getElementById("dvChatMessages");
    const suggestions = document.getElementById("dvChatSuggestions");
    const form = document.getElementById("dvChatForm");
    const input = document.getElementById("dvChatInput");
    const sendButton = document.getElementById("dvSendButton");

    const defaultSuggestions = [
        "What can MRI scans detect?",
        "What are the signs of pneumonia?",
        "How does X-ray imaging work?"
    ];

    /*
     * Optional page-specific suggestions.
     *
     * Example:
     * window.DOCTOR_VISION_SUGGESTIONS = [
     *   "What can MRI scans detect?",
     *   "What are the signs of pneumonia?"
     * ];
     */
    const pageSuggestions =
        window.DOCTOR_VISION_SUGGESTIONS || defaultSuggestions;

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function renderMarkdown(text) {
        if (typeof marked === "undefined") {
            return escapeHtml(text).replace(/\n/g, "<br>");
        }

        return marked.parse(text, {
            breaks: true,
            gfm: true
        });
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function addMessage(role, text, markdown = false) {
        const wrapper = document.createElement("div");
        wrapper.className =
            "dv-chat-message " +
            (role === "user" ? "dv-user-message" : "dv-ai-message");

        const label = document.createElement("div");
        label.className = "dv-message-label";
        label.textContent =
            role === "user" ? "You" : "Dr. Vision";

        const content = document.createElement("div");
        content.className = "dv-message-content";

        if (markdown && role !== "user") {
            content.innerHTML = renderMarkdown(text);
        } else {
            content.textContent = text;
        }

        wrapper.appendChild(label);
        wrapper.appendChild(content);
        messages.appendChild(wrapper);

        scrollToBottom();
        return wrapper;
    }

    function addTypingMessage() {
        const wrapper = document.createElement("div");
        wrapper.className = "dv-chat-message dv-ai-message";
        wrapper.id = "dvTypingMessage";

        wrapper.innerHTML = `
            <div class="dv-message-label">Dr. Vision</div>
            <div class="dv-message-content">
                <span class="dv-typing">
                    <span></span><span></span><span></span>
                </span>
            </div>
        `;

        messages.appendChild(wrapper);
        scrollToBottom();

        return wrapper;
    }

    function setLoading(loading) {
        sendButton.disabled = loading;
        input.disabled = loading;

        if (!loading) {
            input.focus();
        }
    }

    function renderSuggestions() {
        suggestions.innerHTML = "";

        pageSuggestions.forEach(function (question) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "dv-suggestion";
            button.textContent = question;

            button.addEventListener("click", function () {
                input.value = question;
                input.focus();
                autoResize();
            });

            suggestions.appendChild(button);
        });
    }

    function autoResize() {
        input.style.height = "auto";
        input.style.height =
            Math.min(input.scrollHeight, 110) + "px";
    }

    function openChatbot() {
        chatbot.classList.add("open");
        input.focus();
    }

    function closeChatbot() {
        chatbot.classList.remove("open");
    }

    launcher.addEventListener("click", function () {
        if (chatbot.classList.contains("open")) {
            closeChatbot();
        } else {
            openChatbot();
        }
    });

    closeButton.addEventListener("click", closeChatbot);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeChatbot();
        }
    });

    input.addEventListener("input", autoResize);

    input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            form.requestSubmit();
        }
    });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const question = input.value.trim();

        if (!question || sendButton.disabled) {
            return;
        }

        addMessage("user", question);

        input.value = "";
        autoResize();
        setLoading(true);

        const typingMessage = addTypingMessage();

        try {
            const formData = new FormData();
            formData.append("question", question);

            const response = await fetch("/ask", {
                method: "POST",
                body: formData
            });

            let data;

            try {
                data = await response.json();
            } catch (jsonError) {
                throw new Error(
                    "The server returned an invalid response."
                );
            }

            typingMessage.remove();

            if (!response.ok) {
                addMessage(
                    "assistant",
                    data.error ||
                    "The chatbot service is temporarily unavailable."
                );
                return;
            }

            addMessage(
                "assistant",
                data.response ||
                "I could not generate a response.",
                true
            );

        } catch (error) {
            typingMessage.remove();

            console.error("Chatbot request failed:", error);

            addMessage(
                "assistant",
                "I'm unable to connect to the chatbot right now. Please try again later."
            );
        } finally {
            setLoading(false);
        }
    });

    renderSuggestions();
})();

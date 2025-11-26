import os
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from memory_manager import MemoryManager

# Load .env.local
load_dotenv(".env.local")


class Copilot:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        # Model
        self.model = genai.GenerativeModel("models/gemini-2.5-pro")

        # System / persona prompt
        self.system_prompt = AGENT_INSTRUCTION + "\n\n" + SESSION_INSTRUCTION

        # Memory manager (long-term neutral profiles)
        self.memory = MemoryManager()
        self.active_profile = "general"

        # Short-term conversation history (session only)
        self.history = []
        self.turn_count = 0

    # ---------- INTERNAL HELPERS ----------

    def _build_system_with_memory(self) -> str:
        """
        Combine the persona engine with a neutral memory context
        for injection as the leading "setup" message.
        """
        memory_text = self.memory.build_memory_context(self.active_profile)
        return (
            self.system_prompt
            + "\n\n[NEUTRAL MEMORY CONTEXT]\n"
            + memory_text
        )

    def _maybe_summarise(self):
        """
        Balanced summarisation:
        - every ~15 turns
        - only if at least ~10 messages in history
        - saves a neutral summary into long-term memory
        - trims old history to avoid bloat
        """
        if self.turn_count % 15 != 0:
            return
        if len(self.history) < 10:
            return

        # Build a plain-text transcript
        convo_lines = []
        for msg in self.history:
            role = msg.get("role", "user")
            parts = msg.get("parts", [""])
            text = parts[0] if parts else ""
            role_label = "USER" if role == "user" else "COPILOT"
            convo_lines.append(f"{role_label}: {text}")
        transcript = "\n".join(convo_lines)

        prompt = (
            "You are a neutral summariser.\n"
            "Summarise the following conversation in 5–10 bullet points.\n"
            "Focus on: user preferences, facts, decisions, goals, and ongoing tasks.\n"
            "Do NOT imitate any persona or style. Write neutrally.\n\n"
            f"Conversation:\n{transcript}"
        )

        resp = self.model.generate_content(
            contents=[{"role": "user", "parts": [prompt]}]
        )
        summary = resp.text
        self.memory.save_summary(summary)

        # Trim history to last ~20 messages to keep things light
        self.history = self.history[-20:]

    def _handle_command(self, user_input: str):
        """
        Handle explicit memory / control commands.
        Returns a reply string if handled, or None to continue normal flow.
        """
        lower = user_input.lower().strip()

        # Switch profile
        if lower.startswith("switch profile:"):
            name = lower.split(":", 1)[1].strip()
            if name in self.memory.PROFILES:
                self.active_profile = name
                return f"Okay, I’ll focus on the **{name}** memory profile."
            else:
                return (
                    f"I don’t recognise a '{name}' profile. "
                    f"Available profiles: {', '.join(self.memory.PROFILES)}."
                )

        # Wipe memory
        if lower in ("wipe memory", "reset memory", "wipe all memory"):
            self.memory.wipe_all()
            self.history.clear()
            return "All long-term memory has been cleared. Short-term chat history is reset too."

        # List memories
        if lower in ("list memories", "show memories"):
            return self.memory.list_memories()

        # Remember explicit
        if lower.startswith("remember this:") or lower.startswith("remember:"):
            # preserve original casing after ':'
            text = user_input.split(":", 1)[1].strip()
            profile = self.memory.classify(text)
            self.memory.add_memory(profile, text)
            self.memory.save_all()
            return f"Got it. I’ll remember that under the **{profile}** profile."

        # Forget items containing substring
        if lower.startswith("forget:"):
            text = user_input.split(":", 1)[1].strip()
            removed = self.memory.forget_matching(text)
            self.memory.save_all()
            return f"Forgot {removed} matching memory item(s)."

        # Show memory summary context
        if lower in ("summarise memory", "summarize memory", "memory summary"):
            return self.memory.build_memory_context(self.active_profile)

        return None

    # ---------- MAIN RUN ----------

    def run(self, user_input: str) -> str:
        self.turn_count += 1

        # First, check if the user is issuing a memory/control command
        command_reply = self._handle_command(user_input)
        if command_reply is not None:
            # Log this interaction in short-term history as well
            self.history.append(
                {"role": "user", "parts": [user_input]}
            )
            self.history.append(
                {"role": "model", "parts": [command_reply]}
            )
            return command_reply

        # Normal conversational flow
        self.history.append(
            {"role": "user", "parts": [user_input]}
        )

        system_with_mem = self._build_system_with_memory()

        contents = [{"role": "user", "parts": [system_with_mem]}] + self.history

        response = self.model.generate_content(contents=contents)
        reply_text = response.text

        self.history.append(
            {"role": "model", "parts": [reply_text]}
        )

        # Occasionally summarise to keep things efficient
        self._maybe_summarise()

        # Persist long-term memory (if anything changed earlier)
        self.memory.save_all()

        return reply_text


if __name__ == "__main__":
    bot = Copilot()

    print("Copilot (with persistent memory & profiles) is ready.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Copilot: Goodbye.")
            bot.memory.save_all()
            break

        output = bot.run(user_input)
        print("\nCopilot:", output, "\n")

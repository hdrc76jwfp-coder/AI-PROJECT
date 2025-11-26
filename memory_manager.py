import os
import json

MEMORY_DIR = "memory"
PROFILES = ["general", "school", "relationships", "goals", "knowledge"]


class MemoryManager:
    PROFILES = PROFILES

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.memories = {}
        for profile in PROFILES:
            path = self._path(profile)
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        self.memories[profile] = json.load(f)
                except Exception:
                    self.memories[profile] = []
            else:
                self.memories[profile] = []

        self.summary_path = os.path.join(MEMORY_DIR, "summary.txt")
        if os.path.exists(self.summary_path):
            try:
                with open(self.summary_path, "r") as f:
                    self.summary = f.read()
            except Exception:
                self.summary = ""
        else:
            self.summary = ""

    def _path(self, profile: str) -> str:
        return os.path.join(MEMORY_DIR, f"{profile}.json")

    # ---------- SAVE / LOAD ----------

    def save_all(self):
        for profile, items in self.memories.items():
            path = self._path(profile)
            try:
                with open(path, "w") as f:
                    json.dump(items, f, indent=2)
            except Exception as e:
                print(f"Failed to save memory for {profile}:", e)

        try:
            with open(self.summary_path, "w") as f:
                f.write(self.summary)
        except Exception as e:
            print("Failed to save summary:", e)

    def save_summary(self, summary_text: str):
        self.summary = summary_text
        try:
            with open(self.summary_path, "w") as f:
                f.write(summary_text)
        except Exception as e:
            print("Failed to save summary:", e)

    # ---------- CLASSIFICATION ----------

    def classify(self, text: str) -> str:
        """Very simple heuristic classifier for which profile to store text in."""
        t = text.lower()

        if any(k in t for k in ("exam", "test", "gcse", "school", "teacher", "class", "homework", "revision")):
            return "school"
        if any(k in t for k in ("friend", "friends", "crush", "gf", "boyfriend",
                                "girlfriend", "relationship", "mate", "bro", "pooks", "people")):
            return "relationships"
        if any(k in t for k in ("goal", "aim", "dream", "plan", "future", "i want to", "my target", "my goal")):
            return "goals"
        if any(k in t for k in ("fact", "definition", "means", "stands for", "is called", "is when")):
            return "knowledge"
        return "general"

    # ---------- MUTATIONS ----------

    def add_memory(self, profile: str, text: str, source: str = "user"):
        item = {
            "text": text,
            "source": source,
        }
        self.memories.setdefault(profile, []).append(item)

    def forget_matching(self, substring: str) -> int:
        substring = substring.lower()
        removed = 0
        for profile in list(self.memories.keys()):
            new_items = []
            for item in self.memories[profile]:
                if substring in item.get("text", "").lower():
                    removed += 1
                else:
                    new_items.append(item)
            self.memories[profile] = new_items
        return removed

    def wipe_all(self):
        for profile in list(self.memories.keys()):
            self.memories[profile] = []
            path = self._path(profile)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        self.summary = ""
        if os.path.exists(self.summary_path):
            try:
                os.remove(self.summary_path)
            except Exception:
                pass

    # ---------- PRESENTATION ----------

    def list_memories(self) -> str:
        lines = []
        for profile in PROFILES:
            lines.append(f"[{profile}]")
            items = self.memories.get(profile, [])
            if not items:
                lines.append("- (empty)")
            else:
                for item in items[:5]:
                    lines.append(f"- {item['text']}")
            lines.append("")  # blank line between profiles

        if self.summary:
            lines.append("[summary]")
            lines.append(self.summary)

        return "\n".join(lines)

    def build_memory_context(self, active_profile: str) -> str:
        """
        Build a neutral text block summarising relevant memory for injection into the system prompt.
        """
        parts = []

        # Recent items in the active profile
        active_items = self.memories.get(active_profile, [])
        if active_items:
            parts.append(f"Active profile: {active_profile}. Key items:")
            for item in active_items[-5:]:
                parts.append(f"- {item['text']}")

        # Mention other profiles that have data
        other_profiles = [
            p for p in PROFILES
            if p != active_profile and self.memories.get(p)
        ]
        if other_profiles:
            parts.append(f"Other profiles with stored info: {', '.join(other_profiles)}.")

        # Add summary if present
        if self.summary:
            parts.append("Conversation summary:")
            parts.append(self.summary)

        if not parts:
            return "No prior memory stored. Treat this like a fresh conversation."

        return "\n".join(parts)

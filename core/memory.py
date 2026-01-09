class ConversationMemory:
    def __init__(self, max_turns=6):
        self.max_turns = max_turns
        self.history = []

    def add(self, role, content):
        self.history.append((role, content))
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def format(self):
        text = ""
        for role, content in self.history:
            text += f"{role}: {content}\n"
        return text

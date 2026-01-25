from mcp.core.a2a_base_agent import A2AAgent, AgentCard, AgentCapability, A2AMessage
import uuid

"""
Transcript Preprocessing Agent
- Chunks, cleans, or filters transcripts for downstream processing.
"""
class TranscriptPreprocessingAgent(A2AAgent):
    def __init__(self):
        agent_card = AgentCard(
            agent_id="transcript-preprocessing-agent",
            name="Transcript Preprocessing Agent",
            description="Preprocesses meeting transcripts for downstream summarization.",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="process",
                    description="Preprocess transcripts for summarization.",
                    parameters={"transcripts": "list"}
                )
            ]
        )
        super().__init__(agent_card)

    def process(self, transcripts):

        import re
        import unicodedata
        contractions = {
            "can't": "cannot", "won't": "will not", "n't": " not", "'re": " are", "'s": " is", "'d": " would", "'ll": " will", "'t": " not", "'ve": " have", "'m": " am"
        }
        filler_words = [r'\bum\b', r'\buh\b', r'\byou know\b', r'\blike\b', r'\bokay\b', r'\bso\b', r'\bwell\b']
        speaker_tag_pattern = r'^\s*([A-Za-z]+ ?\d*):'
        timestamp_pattern = r'\[\d{1,2}:\d{2}(:\d{2})?\]'
        special_char_pattern = r'[^\w\s.,?!]'

        def expand_contractions(text):
            for k, v in contractions.items():
                text = re.sub(k, v, text)
            return text

        def clean_text(text):
            # Unicode normalization
            text = unicodedata.normalize('NFKC', text)
            # Lowercase
            text = text.lower()
            # Expand contractions
            text = expand_contractions(text)
            # Remove timestamps
            text = re.sub(timestamp_pattern, '', text)
            # Remove speaker tags
            text = re.sub(speaker_tag_pattern, '', text, flags=re.MULTILINE)
            # Remove filler words
            for fw in filler_words:
                text = re.sub(fw, '', text)
            # Remove special characters except basic punctuation
            text = re.sub(special_char_pattern, '', text)
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        processed = []
        chunk_size = 1500
        for t in transcripts:
            t = t.strip()
            if not t:
                continue
            t = clean_text(t)
            words = t.split()
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i+chunk_size])
                processed.append(chunk)
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("application/json", {"processed_transcripts": processed})
        return message

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
        # Chunk each transcript into pieces of up to 1500 words (to match summarizer)
        processed = []
        chunk_size = 1500
        for t in transcripts:
            t = t.strip()
            if not t:
                continue
            words = t.split()
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i+chunk_size])
                processed.append(chunk)
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("application/json", {"processed_transcripts": processed})
        return message

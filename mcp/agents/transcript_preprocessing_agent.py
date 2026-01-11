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
        # Example: chunk each transcript into pieces of chunk_size characters
        processed = []
        for t in transcripts:
            t = t.strip()
            if not t:
                continue
            # Simple chunking by character count
            for i in range(0, len(t), 500):
                processed.append(t[i:i+500])
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("application/json", {"processed_transcripts": processed})
        return message

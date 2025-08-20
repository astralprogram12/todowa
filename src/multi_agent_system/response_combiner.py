# NEW FILE: response_combiner.py
# PUT THIS IN: src/multi_agent_system/

class ResponseCombiner:
    """Combines responses from multiple agents into one smooth response"""
    
    @staticmethod
    def combine_responses(agent_responses, classification):
        """Take multiple agent responses and make them into one good response"""
        
        # If only one agent responded, just return that
        if len(agent_responses) == 1:
            return agent_responses[0]
        
        # Multiple agents responded - combine them smartly
        combined_message = ""
        combined_actions = []
        
        for i, response in enumerate(agent_responses):
            if response.get('message'):
                if i > 0:  # Add separator between agent responses
                    combined_message += "\n\n"
                combined_message += response['message']
            
            # Collect all actions from all agents
            if response.get('actions'):
                combined_actions.extend(response['actions'])
        
        return {
            "message": combined_message.strip(),
            "actions": combined_actions,
            "multi_agent": True,
            "primary_intent": classification.get('primary_intent'),
            "status": "success"
        }
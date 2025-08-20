# response_combiner.py (IMPROVED VERSION)
# Located in: src/multi_agent_system/

class ResponseCombiner:
    """Combines responses from multiple agents intelligently, handling partial failures."""
    
    @staticmethod
    def combine_responses(agent_responses, classification):
        """
        Takes multiple agent responses and creates a single, coherent response.
        Prioritizes error messages over success messages.
        """
        
        # --- [THE FIX] Intelligent failure handling ---
        successes = [r for r in agent_responses if r.get('status') == 'success']
        errors = [r for r in agent_responses if r.get('status') != 'success']
        
        combined_message = ""
        final_status = "success"

        # If there are any errors, the final response is an error.
        if errors:
            final_status = "error"
            
            # Start with what succeeded, if anything.
            if successes:
                success_messages = [s.get('message') for s in successes if s.get('message')]
                if success_messages:
                    combined_message += "I successfully completed part of your request: "
                    combined_message += " and ".join(success_messages)
                    combined_message += ". However, I ran into a problem. "
            
            # Add the first and most important error message.
            error_messages = [e.get('message') for e in errors if e.get('message')]
            if error_messages:
                combined_message += error_messages[0] # Focus on the first error
        
        # If there are no errors, combine the success messages.
        else:
            success_messages = [s.get('message') for s in successes if s.get('message')]
            combined_message = ". ".join(success_messages)

        # --- [END OF FIX] ---

        # Collect all actions from all agents for logging
        combined_actions = []
        for response in agent_responses:
            if response.get('actions'):
                combined_actions.extend(response['actions'])
        
        return {
            "message": combined_message.strip(),
            "actions": combined_actions,
            "multi_agent": len(agent_responses) > 1,
            "primary_intent": classification.get('primary_intent'),
            "status": final_status
        }
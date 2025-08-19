# ReviewCheckk Bot - Smart Response System
import logging
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from debug_framework import debug_tracker, DebugLevel

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    OUT_OF_STOCK = "out_of_stock"

@dataclass
class ResponseContext:
    user_id: int
    platform: str
    url: str
    attempt_count: int
    previous_failures: List[str]
    user_history: Dict
    response_time: float

class SmartResponseSystem:
    """Intelligent response system that adapts based on context and success patterns."""
    
    def __init__(self):
        self.response_templates = {
            ResponseType.SUCCESS: [
                "{message}",
                "✅ {message}",
                "Found: {message}"
            ],
            ResponseType.PARTIAL_SUCCESS: [
                "⚠️ Partial info: {message}",
                "Limited data: {message}",
                "{message} (some details missing)"
            ],
            ResponseType.FAILURE: [
                "❌ Unable to extract product info.",
                "❌ Could not process this link.",
                "❌ Product information not available.",
                "❌ Failed to extract details from this page."
            ],
            ResponseType.ERROR: [
                "❌ An error occurred while processing.",
                "❌ Technical issue encountered.",
                "❌ Please try again in a moment."
            ],
            ResponseType.RATE_LIMITED: [
                "⏳ Please wait a moment before sending another link.",
                "🚫 Too many requests. Please slow down.",
                "⏱️ Rate limit reached. Try again in a few seconds."
            ],
            ResponseType.OUT_OF_STOCK: [
                "📦 This product appears to be out of stock.",
                "❌ Product unavailable or out of stock.",
                "⚠️ This item is currently out of stock."
            ]
        }
        
        self.platform_specific_messages = {
            'amazon': {
                'failure': "❌ Unable to extract from Amazon. Link might be invalid or product unavailable.",
                'success_prefix': ""
            },
            'flipkart': {
                'failure': "❌ Unable to extract from Flipkart. Please check if the link is valid.",
                'success_prefix': ""
            },
            'meesho': {
                'failure': "❌ Unable to extract from Meesho. Product might be unavailable.",
                'success_prefix': ""
            },
            'myntra': {
                'failure': "❌ Unable to extract from Myntra. Fashion item might be out of stock.",
                'success_prefix': ""
            }
        }
        
        self.user_contexts = {}  # Store user interaction history
        
    def generate_response(self, context: ResponseContext, product_data: Optional[Dict] = None) -> Tuple[str, ResponseType]:
        """Generate intelligent response based on context and data quality."""
        try:
            # Update user context
            self._update_user_context(context)
            
            # Determine response type
            response_type = self._determine_response_type(product_data, context)
            
            # Generate appropriate message
            message = self._generate_message(response_type, context, product_data)
            
            # Apply personalization
            message = self._personalize_message(message, context)
            
            # Log response generation
            debug_tracker.log_event(
                DebugLevel.INFO, 'response_system', 'response_generated',
                f'Generated {response_type.value} response for user {context.user_id}',
                {
                    'response_type': response_type.value,
                    'platform': context.platform,
                    'attempt_count': context.attempt_count,
                    'response_time': context.response_time
                },
                user_id=context.user_id,
                url=context.url
            )
            
            return message, response_type
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            debug_tracker.log_event(
                DebugLevel.ERROR, 'response_system', 'generation_error',
                f'Error generating response: {str(e)}',
                {'context': context.__dict__ if context else None}
            )
            return "❌ An unexpected error occurred.", ResponseType.ERROR
    
    def _determine_response_type(self, product_data: Optional[Dict], context: ResponseContext) -> ResponseType:
        """Determine the appropriate response type based on data quality and context."""
        if not product_data:
            return ResponseType.FAILURE
        
        if product_data.get('out_of_stock'):
            return ResponseType.OUT_OF_STOCK
        
        # Check data quality
        quality_score = product_data.get('quality_score', 0)
        
        if quality_score >= 70:
            return ResponseType.SUCCESS
        elif quality_score >= 40:
            return ResponseType.PARTIAL_SUCCESS
        else:
            return ResponseType.FAILURE
    
    def _generate_message(self, response_type: ResponseType, context: ResponseContext, product_data: Optional[Dict]) -> str:
        """Generate message based on response type and context."""
        if response_type == ResponseType.SUCCESS and product_data:
            # Use the formatted message from product parser
            return product_data.get('formatted_message', 'Product information extracted')
        
        elif response_type == ResponseType.PARTIAL_SUCCESS and product_data:
            # Add warning prefix to partial data
            base_message = product_data.get('formatted_message', 'Partial product information')
            return f"⚠️ {base_message} (some details missing)"
        
        else:
            # Use template-based responses for failures/errors
            templates = self.response_templates.get(response_type, self.response_templates[ResponseType.ERROR])
            
            # Check for platform-specific messages
            platform_messages = self.platform_specific_messages.get(context.platform, {})
            if response_type == ResponseType.FAILURE and 'failure' in platform_messages:
                return platform_messages['failure']
            
            # Select template based on user history (avoid repetition)
            user_context = self.user_contexts.get(context.user_id, {})
            recent_responses = user_context.get('recent_responses', [])
            
            # Find a template that wasn't used recently
            for template in templates:
                if template not in recent_responses[-3:]:  # Avoid last 3 responses
                    return template
            
            # If all templates were used recently, use the first one
            return templates[0]
    
    def _personalize_message(self, message: str, context: ResponseContext) -> str:
        """Personalize message based on user interaction history."""
        try:
            user_context = self.user_contexts.get(context.user_id, {})
            
            # Add helpful hints for frequent failures
            failure_count = user_context.get('recent_failure_count', 0)
            if failure_count >= 3 and "❌" in message:
                message += "\n💡 Tip: Try using direct product page links instead of search results."
            
            # Add encouragement for new users
            total_requests = user_context.get('total_requests', 0)
            if total_requests <= 2 and "✅" in message:
                message += "\n🎉 Welcome to ReviewCheckk Bot!"
            
            # Add performance info for slow responses
            if context.response_time > 10:
                message += "\n⏱️ Response took longer than usual due to high traffic."
            
            return message
            
        except Exception as e:
            logger.debug(f"Error personalizing message: {str(e)}")
            return message
    
    def _update_user_context(self, context: ResponseContext):
        """Update user interaction context for personalization."""
        try:
            user_id = context.user_id
            
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'recent_responses': [],
                    'recent_failure_count': 0,
                    'preferred_platforms': {},
                    'last_interaction': time.time()
                }
            
            user_ctx = self.user_contexts[user_id]
            user_ctx['total_requests'] += 1
            user_ctx['last_interaction'] = time.time()
            
            # Track platform preferences
            platform = context.platform
            if platform in user_ctx['preferred_platforms']:
                user_ctx['preferred_platforms'][platform] += 1
            else:
                user_ctx['preferred_platforms'][platform] = 1
            
            # Track recent failures for hints
            if context.previous_failures:
                user_ctx['recent_failure_count'] = len(context.previous_failures)
            else:
                user_ctx['recent_failure_count'] = max(0, user_ctx['recent_failure_count'] - 1)
            
            # Cleanup old contexts (keep only last 100 users)
            if len(self.user_contexts) > 100:
                # Remove oldest contexts
                sorted_users = sorted(
                    self.user_contexts.items(),
                    key=lambda x: x[1]['last_interaction']
                )
                for old_user_id, _ in sorted_users[:-100]:
                    del self.user_contexts[old_user_id]
                    
        except Exception as e:
            logger.debug(f"Error updating user context: {str(e)}")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user interaction statistics."""
        user_ctx = self.user_contexts.get(user_id, {})
        return {
            'total_requests': user_ctx.get('total_requests', 0),
            'successful_requests': user_ctx.get('successful_requests', 0),
            'success_rate': (user_ctx.get('successful_requests', 0) / max(1, user_ctx.get('total_requests', 1))) * 100,
            'preferred_platforms': user_ctx.get('preferred_platforms', {}),
            'recent_failure_count': user_ctx.get('recent_failure_count', 0)
        }
    
    def should_show_help(self, user_id: int) -> bool:
        """Determine if user should be shown help based on their interaction pattern."""
        user_ctx = self.user_contexts.get(user_id, {})
        
        # Show help for new users after 2 failures
        if user_ctx.get('total_requests', 0) <= 5 and user_ctx.get('recent_failure_count', 0) >= 2:
            return True
        
        # Show help for users with consistently low success rate
        total_requests = user_ctx.get('total_requests', 0)
        successful_requests = user_ctx.get('successful_requests', 0)
        
        if total_requests >= 10:
            success_rate = (successful_requests / total_requests) * 100
            if success_rate < 30:
                return True
        
        return False

# Global response system instance
smart_response_system = SmartResponseSystem()

def generate_smart_response(user_id: int, platform: str, url: str, 
                          product_data: Optional[Dict] = None,
                          attempt_count: int = 1, previous_failures: List[str] = None,
                          response_time: float = 0.0) -> Tuple[str, str]:
    """Generate smart response using the global response system."""
    
    context = ResponseContext(
        user_id=user_id,
        platform=platform,
        url=url,
        attempt_count=attempt_count,
        previous_failures=previous_failures or [],
        user_history={},
        response_time=response_time
    )
    
    message, response_type = smart_response_system.generate_response(context, product_data)
    return message, response_type.value

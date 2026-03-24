"""
Slack event handlers for emoji reactions.
Processes reaction events and triggers Airtable record creation.
"""

import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import get_settings
from app.utils.logging import logger
from app.slack.client import slack_client
from app.airtable.client import airtable_client

# Map emojis to their corresponding Pain Score values in Airtable.
# The original :fedex: emoji is kept for backward compatibility and does not set a score.
EMOJI_PAIN_SCORE_MAP = {
    "papercut-small": "sm",
    "papercut-md": "md",
    "papercut-big": "lg",
    "fedex": None,  # or you could map this to a default pain score like "sm"
}

# Map emojis to their Airtable destinations (base, table, field) and pain scores
EMOJI_DESTINATION_MAP = {
    # Pain Points emojis (original base)
    "papercut-small": {
        "base_id_key": "airtable_base_id",
        "table_name_key": "airtable_table_name",
        "field_name_key": "airtable_field_name",
        "pain_score": "sm",
        "slack_link_field_name": "Slack Thread"
    },
    "papercut-md": {
        "base_id_key": "airtable_base_id",
        "table_name_key": "airtable_table_name", 
        "field_name_key": "airtable_field_name",
        "pain_score": "md",
        "slack_link_field_name": "Slack Thread"
    },
    "papercut-big": {
        "base_id_key": "airtable_base_id",
        "table_name_key": "airtable_table_name",
        "field_name_key": "airtable_field_name", 
        "pain_score": "lg",
        "slack_link_field_name": "Slack Thread"
    },
    "papercut-immediate-in-progress": {
        "base_id_key": "airtable_base_id",
        "table_name_key": "airtable_table_name",
        "field_name_key": "airtable_field_name", 
        "pain_score": "lg",
        "status": "In Progress",
        "slack_link_field_name": "Slack Thread"
    },
    "fedex": {
        "base_id_key": "airtable_base_id",
        "table_name_key": "airtable_table_name",
        "field_name_key": "airtable_field_name",
        "pain_score": None
    },
    # Changelog emoji (separate base)
    "changelog": {
        "base_id_key": "changelog_airtable_base_id",
        "table_name_key": "changelog_airtable_table_name",
        "field_name_key": "changelog_airtable_field_name",
        "pain_score": None
    },
    # Content Ideas emojis (separate base)
    "content-twitter-article": {
        "base_id_key": "content_ideas_airtable_base_id",
        "table_name_key": "content_ideas_airtable_table_name",
        "field_name_key": "content_ideas_airtable_field_name",
        "pain_score": None,
        "content_type": "Twitter Article",
        "slack_link_field_name": "Slack Thread"
    },
    "content-twitter-post": {
        "base_id_key": "content_ideas_airtable_base_id",
        "table_name_key": "content_ideas_airtable_table_name",
        "field_name_key": "content_ideas_airtable_field_name",
        "pain_score": None,
        "content_type": "Twitter Post",
        "slack_link_field_name": "Slack Thread"
    },
    "content-blog-post": {
        "base_id_key": "content_ideas_airtable_base_id",
        "table_name_key": "content_ideas_airtable_table_name",
        "field_name_key": "content_ideas_airtable_field_name",
        "pain_score": None,
        "content_type": "Blog Post",
        "slack_link_field_name": "Slack Thread"
    }
}


def get_assignee_name(user_id: str) -> Optional[str]:
    """
    Look up the Airtable Assignee name for a Slack user ID.
    
    Args:
        user_id: The Slack user ID
        
    Returns:
        The Assignee name if found, None otherwise
    """
    try:
        settings = get_settings()
        user_map = json.loads(settings.slack_user_map)
        return user_map.get(user_id)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error parsing SLACK_USER_MAP: {e}")
        return None


def handle_reaction_added(event: Dict[str, Any]) -> bool:
    """
    Handle reaction_added event from Slack.
    
    Args:
        event: The reaction event data from Slack
        
    Returns:
        True if processed successfully, False otherwise
    """
    try:
        # Extract event data
        reaction = event.get("reaction")

        # Check if the reaction is one of our target emojis. If not, ignore it.
        if reaction not in EMOJI_DESTINATION_MAP:
            logger.debug(f"Ignoring non-target emoji: {reaction}")
            return True  # Acknowledge the event, but do nothing

        # Get the destination configuration and pain score for the emoji
        emoji_config = EMOJI_DESTINATION_MAP.get(reaction)
        pain_score = emoji_config.get("pain_score") if emoji_config else None

        user_id = event.get("user")
        item = event.get("item", {})
        channel_id = item.get("channel")
        message_ts = item.get("ts")
        thread_ts = item.get("thread_ts")  # Present if message is in a thread
        
        # Log the reaction event
        logger.slack_event("reaction_added", user_id, channel_id, f"Reaction: {reaction}")

        # Validate required fields
        if not all([user_id, channel_id, message_ts]):
            logger.error("Missing required fields in reaction event", {
                "user_id": user_id,
                "channel_id": channel_id,
                "message_ts": message_ts
            })
            return False
        
        # Get the original message (supports both regular and threaded messages automatically)
        message = slack_client.get_message_info(channel_id, message_ts)
        if not message:
            logger.error("Could not retrieve message", {
                "channel_id": channel_id,
                "message_ts": message_ts,
                "thread_ts": thread_ts,
                "is_threaded": thread_ts is not None
            })
            return False
        
        # Extract message text
        message_text = message.get("text", "")
        if not message_text:
            logger.warning("Message has no text content", {
                "channel_id": channel_id,
                "message_ts": message_ts
            })
            return False
        
        # Get additional context for logging
        message_user_id = message.get("user")
        user_info = slack_client.get_user_info(user_id)
        channel_info = slack_client.get_channel_info(channel_id)
        
        # Look up assignee name from Slack user ID
        assignee_name = get_assignee_name(user_id)
        
        # Get content type if specified in emoji config
        content_type = emoji_config.get("content_type") if emoji_config else None
        
        # Get Slack permalink if this emoji requires it
        slack_link = None
        if emoji_config and emoji_config.get("slack_link_field_name"):
            slack_link = slack_client.get_message_permalink(channel_id, message_ts)
        
        # Create context for logging
        context = {
            "reactor_user": user_info.get("name") if user_info else user_id,
            "message_author": message_user_id,
            "channel_name": channel_info.get("name") if channel_info else channel_id,
            "message_length": len(message_text),
            "is_threaded": thread_ts is not None,
            "thread_ts": thread_ts,
            "timestamp": datetime.utcnow().isoformat(),
            "pain_score": pain_score,  # Add pain score to context
            "emoji_config": emoji_config,  # Add emoji configuration to context
            "assignee_name": assignee_name,  # Add assignee name to context
            "content_type": content_type,  # Add content type to context
            "slack_link": slack_link,  # Add slack link to context
        }
        
        logger.info(f"Processing {reaction} reaction", context)
        
        # Create Airtable record
        success = create_airtable_record(message_text, message, context)
        
        if success:
            logger.info(f"Successfully processed {reaction} reaction", context)
            return True
        else:
            logger.error(f"Failed to process {reaction} reaction", context)
            return False
            
    except Exception as e:
        logger.error("Error handling reaction event", {
            "error": str(e),
            "event": event
        })
        return False


def extract_image_attachments(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts image attachments from Slack message and prepares URLs for Airtable.

    Args:
        message: The Slack message object.

    Returns:
        A list of dictionaries, where each contains the filename and authenticated URL.
    """
    attachments = []
    files = message.get("files", [])
    settings = get_settings()

    for file in files:
        mimetype = file.get("mimetype", "")
        if mimetype.startswith("image/"):
            url_private = file.get("url_private")
            filename = file.get("name", "screenshot.png")
            
            if url_private:
                # Create authenticated URL with bot token
                auth_url = f"{url_private}?token={settings.slack_bot_token}"
                
                attachments.append({
                    "filename": filename,
                    "url": auth_url
                })
                
                logger.info(f"Found image attachment: {filename}", context={"url": url_private})

    return attachments


def create_airtable_record(message_text: str, message: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Create a record in Airtable with the message text and any image attachments.
    
    Args:
        message_text: The text content of the message
        message: The full Slack message object
        context: Additional context for logging
        
    Returns:
        True if record created successfully, False otherwise
    """
    try:
        # Get emoji configuration and settings
        emoji_config = context.get("emoji_config")
        settings = get_settings()
        
        # Get the correct base, table, and field for this emoji
        base_id_key = emoji_config.get("base_id_key")
        table_name_key = emoji_config.get("table_name_key")
        field_name_key = emoji_config.get("field_name_key")
        
        # Get the actual values from settings using the keys
        base_id = getattr(settings, base_id_key)
        table_name = getattr(settings, table_name_key)
        field_name = getattr(settings, field_name_key)
        
        # Prepare record fields - only add Status if not a content idea emoji
        fields = {
            field_name: message_text,
        }
        
        # Add Status field unless this is a content idea (which doesn't use Status)
        if not emoji_config.get("content_type"):
            status = emoji_config.get("status", "Intake")
            fields["Status"] = status

        # Add pain score to the record if it exists
        pain_score = context.get("pain_score")
        if pain_score:
            fields["Pain Score"] = pain_score

        # Add assignee if we have a mapping for this user (skip for content emojis)
        assignee_name = context.get("assignee_name")
        if assignee_name and not emoji_config.get("content_type"):
            fields["Assignee"] = assignee_name
        
        # Add content type if it exists
        content_type = context.get("content_type")
        if content_type:
            fields["Type of Content"] = content_type
        
        # Add Slack link if it exists and field name is specified
        slack_link = context.get("slack_link")
        slack_link_field_name = emoji_config.get("slack_link_field_name")
        if slack_link and slack_link_field_name:
            fields[slack_link_field_name] = slack_link

        # Add image attachments if any are present
        image_attachments = extract_image_attachments(message)
        
        # Create the record with or without attachments
        if image_attachments:
            logger.info(f"Creating record with {len(image_attachments)} image attachments")
            record = airtable_client.create_record_with_attachments(fields, image_attachments, base_id, table_name)
        else:
            logger.info("Creating record without attachments")
            record = airtable_client.create_record(fields, base_id, table_name)
        
        if record:
            logger.info("Airtable record created successfully", {
                "record_id": record["id"],
                "message_preview": message_text[:100] + "..." if len(message_text) > 100 else message_text,
                **context
            })
            return True
        else:
            logger.error("Failed to create Airtable record", {
                "message_preview": message_text[:100] + "..." if len(message_text) > 100 else message_text,
                **context
            })
            return False
            
    except Exception as e:
        logger.error("Error creating Airtable record", {
            "error": str(e),
            "message_preview": message_text[:100] + "..." if len(message_text) > 100 else message_text,
            **context
        })
        return False


def handle_reaction_removed(event: Dict[str, Any]) -> bool:
    """
    Handle reaction_removed event from Slack.
    Currently just logs the event - no action taken.
    
    Args:
        event: The reaction event data from Slack
        
    Returns:
        True always (no processing needed)
    """
    reaction = event.get("reaction")
    user_id = event.get("user")
    channel_id = event.get("item", {}).get("channel")
    
    logger.slack_event("reaction_removed", user_id, channel_id, f"Reaction: {reaction}")
    
    # For now, we don't do anything when reactions are removed
    # This could be extended to remove records from Airtable if needed
    return True

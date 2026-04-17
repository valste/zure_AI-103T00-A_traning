from pathlib import Path
import base64
from typing import Union

import os
from dotenv import load_dotenv

# use this for asynch mode
# from azure.ai.projects.aio import AIProjectClient
# from azure.identity.aio import DefaultAzureCredential

# -> synchronous credential for Azure SDK clients
from azure.ai.projects import AIProjectClient
from azure.identity import (
    DefaultAzureCredential,
)


def save_image(image_data: Union[str, bytes], filename: str) -> Path:
    """
    Save base64-encoded image data to a file.

    Args:
        image_data: Base64 string or bytes
        filename: Output filename (e.g., "image.png")

    Returns:
        Path to the saved file
    """
    output_dir = Path("agent_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / filename

    # Ensure input is bytes
    if isinstance(image_data, str):
        image_bytes = base64.b64decode(image_data)
    else:
        image_bytes = base64.b64decode(image_data)

    file_path.write_bytes(image_bytes)

    return file_path


def main() -> None:
    """Initialize configuration for the agent client."""

    load_dotenv(
        override=True
    )  # Load environment variables from .env file, allowing overridess

    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    agent_name = os.getenv("AGENT_NAME", "it-support-agent")

    if not project_endpoint:
        print("Error: PROJECT_ENDPOINT environment variable not set")
        print("Please set it in your .env file or environment")
        return

    print("Connecting to Microsoft Foundry project...")
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(credential=credential, endpoint=project_endpoint)

    # Get the OpenAI client for Responses API
    openai_client = project_client.get_openai_client()

    # Get the agent created in the portal
    print(f"Loading agent: {agent_name}")
    agent = project_client.agents.get(agent_name=agent_name)

    # from pprint import pprint
    # pprint(agent)

    # what is the version of the running agent instance?
    latest = agent.versions.get("latest", {})
    resolved_version = latest.get("version")

    print(
        f"Connected to agent: {agent.name} | version: {resolved_version} | id: {agent.id})"
    )

    # Create a conversation
    conversation = openai_client.conversations.create(items=[])
    print(f"Conversation created (id: {conversation.id})")

    # Chat loop
    print("\n" + "=" * 60)
    print("IT Support Agent Ready!")
    print("Ask questions, request data analysis, or get help.")
    print("Type 'exit' to quit.")
    print("=" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Add user message to conversation
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[{"type": "message", "role": "user", "content": user_input}],
        )

        # Get response from agent
        print("\n[Agent is thinking...]")
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"}
            },
            input="",
        )

        # Display response
        if hasattr(response, "output_text") and response.output_text:
            print(f"\nAgent: {response.output_text}\n")
        elif hasattr(response, "output") and response.output:
            # Extract text from output items
            image_count = 0
            for item in response.output:
                if hasattr(item, "text") and item.text:
                    print(f"\nAgent: {item.text}\n")
                elif hasattr(item, "type"):
                    # Handle other output types like images from code interpreter
                    if item.type == "image":
                        image_count += 1
                        filename = f"chart_{image_count}.png"

                        # Download and save the image
                        if hasattr(item, "image") and hasattr(item.image, "data"):
                            filepath = save_image(item.image.data, filename)
                            print(f"\n[Agent generated a chart - saved to: {filepath}]")
                        else:
                            print(f"\n[Agent generated an image]")
                    elif item.type == "file":
                        print(f"\n[Agent created a file]")

        # Check for files in the response and download them
        file_id = ""
        filename = ""
        container_id = ""

        # Get the last message which should contain file citations
        last_message = response.output[-1]
        if (
            last_message.type == "message"
            and last_message.content
            and last_message.content[-1].type == "output_text"
            and last_message.content[-1].annotations
        ):
            # Extract file information from response annotations
            file_citation = last_message.content[-1].annotations[-1]
            if file_citation.type == "container_file_citation":
                file_id = file_citation.file_id
                filename = file_citation.filename
                container_id = file_citation.container_id

        # Download the generated file if available
        if file_id and filename:
            file_content = openai_client.containers.files.content.retrieve(
                file_id=file_id, container_id=container_id
            )
            output_dir = Path("agent_outputs")
            output_dir.mkdir(exist_ok=True)
            file_path = output_dir / filename
            with open(file_path, "wb") as f:
                f.write(file_content.read())
            print(f"File downloaded successfully: {file_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Program finished.")

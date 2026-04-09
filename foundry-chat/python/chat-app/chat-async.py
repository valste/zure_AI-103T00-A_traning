import os
from dotenv import load_dotenv

# import namespaces for async
import asyncio
from openai import AsyncOpenAI
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider


async def main():

    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    try:
        # Get configuration settings
        load_dotenv()
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        # Initialize an async OpenAI client
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://ai.azure.com/.default"
        )

        async_client = AsyncOpenAI(
            base_url=azure_openai_endpoint, api_key=token_provider
        )

        # some glocals
        last_response_id = None
        instructions = "You are a helpful AI assistant that explains technology concepts clearly."
        streaming_enabled = False  # Set to True to enable streaming responses (if supported by your environment and model)

        # Loop until the user wants to quit
        print("Assistant: Enter a prompt (or type 'quit' to exit)")
        print("Options:\n\t* Toggle streaming mode by typing streaming:on/off")
        while True:
            input_text = input("\nYou: ")
            if input_text.lower() == "quit":
                print("Assistant: Goodbye!")
                break
            elif input_text.lower() == "streaming:on":
                streaming_enabled = True
                print("Assistant: Streaming mode enabled.")
                continue
            elif input_text.lower() == "streaming:off":
                streaming_enabled = False
                print("Assistant: Streaming mode disabled.")
                continue

            # ----------------OpenAI client with responses API-------------------------
            if streaming_enabled:
                # For streaming responses, you would typically handle the stream of data as it arrives.
                stream = await async_client.responses.create(
                    model=model_deployment,
                    instructions=instructions,
                    input=input_text,
                    previous_response_id=last_response_id,
                    stream=True,
                )

                async for event in stream:
                    if event.type == "response.output_text.delta":
                        print(event.delta, end="")
                    elif event.type == "response.completed":
                        last_response_id = event.response.id
                
                print()

            else:
                # non-streaming response handling
                response = await async_client.responses.create(
                    model=model_deployment,
                    instructions=instructions,
                    input=input_text,
                    previous_response_id=last_response_id,
                )
                last_response_id = response.id
                assistant_text = response.output_text
                print("\nAssistant:", assistant_text)

    except Exception as ex:
        print("An error occurred:", ex)

    finally:
        # Close the async client session
        await credential.close()
        # await async_client.close()  # TODO clarify why doesn't work


if __name__ == "__main__":
    asyncio.run(main())

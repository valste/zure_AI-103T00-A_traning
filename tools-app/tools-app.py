import os
from dotenv import load_dotenv
import glob, time

# import namespaces
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# lets combine all tools together in one app

def main():
    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    # Function to get the current time
    def get_time():
        return f"The time is {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"

    function_tools = [
        {
            "type": "function",
            "name": "get_time",
            "description": "Get the current time",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    ]

    try:
        # Get configuration settings
        load_dotenv(override=True)
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        # Initialize the OpenAI client
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://ai.azure.com/.default"
        )

        openai_client = OpenAI(base_url=azure_openai_endpoint, api_key=token_provider)

        # Create vector store and upload files
        print("Creating vector store and uploading files...")
        vector_store = openai_client.vector_stores.create(name="travel-brochures")
        file_streams = [open(f, "rb") for f in glob.glob("brochures/*.pdf")]
        if not file_streams:
            print("No PDF files found in the brochures folder!")
            return
        file_batch = openai_client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
        )
        for f in file_streams:
            f.close()
        print(f"Vector store created with {file_batch.file_counts.completed} files.")

        # Track conversation state
        last_response_id = None
        # Initialize messages with a system prompt
        messages = [
            {
                "role": "developer",
                "content": "You are an AI assistant that provides information.",
            },
        ]

        # Loop until the user wants to quit
        while True:
            input_text = input('\nEnter a question (or type "quit" to exit): ')
            if input_text.lower() == "quit":
                break
            if len(input_text) == 0:
                print("Please enter a question.")
                continue

            # Append the user prompt to the messages
            messages.append({"role": "user", "content": input_text})

            # Get a response using tools
            # Get a response using tools
            response = openai_client.responses.create(
                model=model_deployment,
                instructions="""
                You are a travel assistant that provides information on travel services available from Margie's Travel.
                Answer questions about services offered by Margie's Travel using the provided travel brochures.
                Search the web for general information about destinations or current travel advice.
                """,
                input=input_text,
                previous_response_id=last_response_id,
                tools=[
                    {"type": "file_search", "vector_store_ids": [vector_store.id]},
                    function_tools[0],
                    {"type": "web_search_preview"},
                ],
            )

            # Append model output to the messages
            messages += response.output

            # Was there a function call?
            # return the tool output as a follow up response
            for item in response.output:
                if item.type == "function_call" and item.name == "get_time":
                    current_time = get_time()
                    messages.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": current_time,
                        }
                    )

                    # Get a follow up response using the tool output
                    response = openai_client.responses.create(
                        model=model_deployment,
                        instructions="Answer only with the tool output.",
                        input=messages,
                        tools=function_tools,
                    )

            print(response.output_text)
            last_response_id = response.id

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()

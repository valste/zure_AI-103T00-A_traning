import os
from dotenv import load_dotenv

# import namespaces
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os


def main():

    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    try:

        # Get configuration settings
        load_dotenv() # the .env file is in the same directory as this script

        model_deployment = os.getenv("MODEL_DEPLOYMENT")
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        # api_key = os.getenv("API_KEY")        

        # Initialize the project client 
        # set token provider
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://ai.azure.com/.default"
        )

        # Get a chat client
        openai_client = OpenAI(base_url=azure_openai_endpoint, api_key=token_provider)
        #openai_client = OpenAI(base_url=azure_openai_endpoint, api_key=api_key)

        # Track responses
        last_response_id = None
        
        # Loop until the user types 'quit'
        while True:
            # Get input text
            input_text = input("Enter the prompt (or type 'quit' to exit): ")
            if input_text.lower() == "quit":
                break
            if len(input_text) == 0:
                print("Please enter a prompt.")
                continue

            # --unsing chat completions API------
            
            # # Get a chat completion
            # completion = openai_client.chat.completions.create(
            #     model=str(model_deployment),
            #     messages=[
            #         {
            #             "role": "system",
            #             "content": "You are a helpful AI assistant that answers questions and provides information.",
            #         },
            #         {"role": "user", "content": input_text},
            #     ],
            # )
            # print(completion.choices[0].message.content)
            
            ##-----using responses API------
            
            # # Get a response
            # response = openai_client.responses.create(
            #             model=model_deployment,
            #             instructions="You are a helpful AI assistant that answers questions and provides information.",
            #             input=input_text,
            #             previous_response_id=last_response_id,
            #         )
            # print(response.output_text)
            # last_response_id = response.id
            
            #--using streaming responses API------
            
            # Get a response
            stream = openai_client.responses.create(
                        model=model_deployment,
                        instructions="You are a helpful AI assistant that answers questions and provides information.",
                        input=input_text,
                        previous_response_id=last_response_id,
                        stream=True
            )
            for event in stream:
                if event.type == "response.output_text.delta":
                    print(event.delta, end="")
                elif event.type == "response.completed":
                    last_response_id = event.response.id
            print()


    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()

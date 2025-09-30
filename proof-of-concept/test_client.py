import asyncio
import websockets
import base64


async def test_websocket():
    uri = "ws://localhost:8765"

    # Read a sample audio file
    try:
        with open("sample_audio.m4a", "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        async with websockets.connect(uri) as websocket:
            print("Connected to server")

            # Send audio data
            await websocket.send(audio_base64)
            print("Audio sent")

            # Wait for response
            response = await websocket.recv()
            print(f"Received transcription: {response}")

    except FileNotFoundError:
        print("Error: sample_audio.m4a not found")
        print("Please provide a sample audio file named 'sample_audio.m4a'")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())

import whisper
import asyncio
import websockets
import base64
import tempfile
import os


model = whisper.load_model("base")


async def audio_server(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            # Assuming base64 encoded audio chunks
            audio_data_decoded = base64.b64decode(message)
            print(f"Received audio chunk (length: {len(audio_data_decoded)} bytes)")

            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as temp_audio:
                temp_audio.write(audio_data_decoded)
                temp_audio_path = temp_audio.name

            try:
                # Transcribe the audio file
                result = model.transcribe(temp_audio_path, fp16=False)

                # Save transcription
                with open("transcription.txt", "w") as f:
                    f.write(result["text"])

                print(f"Transcription complete: {result['text']}")

                # Send transcription back to client
                await websocket.send(result["text"])
            finally:
                # Clean up temporary file
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected normally")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    async with websockets.serve(audio_server, "localhost", 8765):
        print("Server started on ws://localhost:8765")
        await asyncio.Future() 

if __name__ == "__main__":
    asyncio.run(main())




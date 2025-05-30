# Rooster
What does a rooster say?

## Data Collection
Tracks were collected from actual people contacted by the Rooster team via Telegram and Whatsapp as voice messages. The data is stored in the `data` folder locally to be shared with the team for analysis.

## Preprocessing Steps:
All tracks were converted to 16kHz mono wav files with ffmpeg.

## Conversion to WAV command:

"ffmpeg -i File1.ogg -ar 16000 -ac 1 File1.wav" 
"ffmpeg -i File1.opus -ar 16000 -ac 1 File1.wav"

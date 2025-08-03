import os
import torch
import speech_recognition as sr
from transformers import AutoModelForCausalLM, AutoTokenizer
from gtts import gTTS
import pyttsx3
from playsound import playsound
from collections import deque
import hashlib
from multiprocessing import Process

class OptimizedVoiceChatBot:
    def __init__(self, model_name="microsoft/DialoGPT-medium"):
        # Model initialization
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)

        # Ensure pad token is set
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # Device optimization
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        
        # Speech components
        self.recognizer = sr.Recognizer()
        self.tts_engine = None  
        self.speech_enabled = True
        
        # Conversation management
        self.conversation_history = deque(maxlen=5)  # More dynamic conversation history
        
        # Configure microphone
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except:
            self.speech_enabled = False
    
    def configure_tts(self):
        """Optimized TTS configuration with validation"""
        print("\nTTS Configuration:")
        print("1. gTTS (Online)")
        print("2. pyttsx3 (Offline)")
        print("3. Text Only")
        
        while True:
            choice = input("Choose (1-3): ").strip()
            if choice == "1":
                try:
                    test = gTTS(text="TTS test", lang='en')
                    test.save("test.mp3")
                    playsound("test.mp3")
                    os.remove("test.mp3")
                    self.tts_engine = "gtts"
                    break
                except:
                    print("gTTS failed.")
            elif choice == "2":
                try:
                    engine = pyttsx3.init()
                    engine.say("TTS test")
                    engine.runAndWait()
                    self.tts_engine = engine
                    break
                except:
                    print("pyttsx3 failed.")
            elif choice == "3":
                self.tts_engine = None
                break

    def get_tts_filename(self, text):
        """Generate a unique filename for caching TTS responses"""
        return f"tts_cache/{hashlib.md5(text.encode()).hexdigest()}.mp3"

    def play_audio(self, filename):
        """Non-blocking audio playback"""
        playsound(filename)
    
    def listen(self):
        """Optimized speech recognition with fallback"""
        if not self.speech_enabled:
            return input("You: ").strip()
        
        try:
            with sr.Microphone() as source:
                print("\nListening... (speak now)")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio)
                print(f"You: {text}")
                return text.strip()
        except sr.UnknownValueError:
            print("Could not understand audio, please repeat.")
            return input("You (type): ").strip()
        except:
            return input("You (type): ").strip()
    
    def speak(self, text):
        """Optimized speech output with caching"""
        print(f"Bot: {text}")
        if not self.tts_engine:
            return
        
        try:
            if self.tts_engine == "gtts":
                filename = self.get_tts_filename(text)
                if not os.path.exists(filename):
                    tts = gTTS(text=text, lang='en')
                    tts.save(filename)
                p = Process(target=self.play_audio, args=(filename,))
                p.start()
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
        except Exception as e:
            print(f"Speech error: {e}")
    
    def generate_response(self, user_input):
        """Optimized response generation with better context handling"""
        self.conversation_history.append(f"User: {user_input}")
        prompt = "\n".join(self.conversation_history) + "\nAssistant:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, padding=True).to(self.device)
        
        with torch.no_grad():
            output = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=inputs.input_ids.shape[1] + 60,
                temperature=0.7,
                top_k=40,
                top_p=0.9,
                repetition_penalty=1.2,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(output[:, inputs.input_ids.shape[1]:][0], skip_special_tokens=True).strip()
        response = response.split("\n")[0]
        self.conversation_history.append(f"Assistant: {response}")
        return response
    
    def run(self):
        """Optimized main conversation loop"""
        print("\n=== Voice Chat Bot ===")
        self.configure_tts()
        self.speak("Hello! How can I help you today?")
        
        while True:
            user_input = self.listen()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'bye']:
                self.speak("Goodbye!")
                break
            
            response = self.generate_response(user_input)
            self.speak(response)

if __name__ == "__main__":
    os.makedirs("tts_cache", exist_ok=True)  # Ensure cache directory exists
    bot = OptimizedVoiceChatBot()
    bot.run()
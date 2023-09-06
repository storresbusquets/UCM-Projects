from transformers import pipeline, T5Tokenizer, T5ForConditionalGeneration

class GradioInference():
    def __init__(self):
        self.sizes = list(whisper._MODELS.keys())
        self.langs = ["none"] + sorted(list(whisper.tokenizer.LANGUAGES.values()))
        self.current_size = "base"
        self.loaded_model = whisper.load_model(self.current_size)
        self.yt = None
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Initialize VoiceLabT5 model and tokenizer
        self.keyword_model = T5ForConditionalGeneration.from_pretrained("Voicelab/vlt5-base-keywords")
        self.keyword_tokenizer = T5Tokenizer.from_pretrained("Voicelab/vlt5-base-keywords")

        # Sentiment Classifier
        self.classifier = pipeline("text-classification")

    def __call__(self, link, lang, size):
        if self.yt is None:
            self.yt = YouTube(link)
        path = self.yt.streams.filter(only_audio=True)[0].download(filename="tmp.mp4")

        if lang == "none":
            lang = None

        if size != self.current_size:
            self.loaded_model = whisper.load_model(size)
            self.current_size = size
        results = self.loaded_model.transcribe(path, language=lang)

        # Perform summarization on the transcription
        transcription_summary = self.summarizer(results["text"], max_length=130, min_length=30, do_sample=False)

        # Extract keywords using VoiceLabT5
        task_prefix = "Keywords: "
        input_sequence = task_prefix + results["text"]
        input_ids = self.keyword_tokenizer(input_sequence, return_tensors="pt", truncation=False).input_ids
        output = self.keyword_model.generate(input_ids, no_repeat_ngram_size=3, num_beams=4)
        predicted = self.keyword_tokenizer.decode(output[0], skip_special_tokens=True)
        keywords = [x.strip() for x in predicted.split(',') if x.strip()]

        label = self.classifier(results["text"])[0]["label"]
        
        return results["text"], transcription_summary[0]["summary_text"], keywords, label

    def populate_metadata(self, link):
        self.yt = YouTube(link)
        return self.yt.thumbnail_url, self.yt.title


def transcribe_audio(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result["text"]


gio = GradioInference()
title = "Youtube Insights"
description = "Your AI-powered video analytics tool"

block = gr.Blocks()
with block as demo:
    gr.HTML(
        """
        <div style="text-align: center; max-width: 500px; margin: 0 auto;">
          <div>
            <h1>Youtube <span style="color: red;">Insights</span> 📹</h1>
          </div>
          <p style="margin-bottom: 10px; font-size: 94%">
            Your AI-powered video analytics tool
          </p>
        </div>
        """
    )
    with gr.Group():
        with gr.Tab("From YouTube"):
            with gr.Box():
                with gr.Row().style(equal_height=True):
                    size = gr.Dropdown(label="Model Size", choices=gio.sizes, value='base')
                    lang = gr.Dropdown(label="Language (Optional)", choices=gio.langs, value="none")
                link = gr.Textbox(label="YouTube Link")
                title = gr.Label(label="Video Title")
                with gr.Row().style(equal_height=True):
                    img = gr.Image(label="Thumbnail")
                    text = gr.Textbox(label="Transcription", placeholder="Transcription Output", lines=10)
                with gr.Row().style(equal_height=True):
                    summary = gr.Textbox(label="Summary", placeholder="Summary Output", lines=5)
                    keywords = gr.Textbox(label="Keywords", placeholder="Keywords Output", lines=5)
                    label = gr.Label(label="Sentiment Analysis")
                with gr.Row().style(equal_height=True):
                    btn = gr.Button("Get video insights")  # Updated button label
                btn.click(gio, inputs=[link, lang, size], outputs=[text, summary, keywords, label])
                link.change(gio.populate_metadata, inputs=[link], outputs=[img, title])

        with gr.Tab("From Audio file"):
            with gr.Box():
                with gr.Row().style(equal_height=True):
                    size = gr.Dropdown(label="Model Size", choices=gio.sizes, value='base')
                    lang = gr.Dropdown(label="Language (Optional)", choices=gio.langs, value="none")
                audio_file = gr.Audio(type="filepath")
                with gr.Row().style(equal_height=True):
                    # img = gr.Image(label="Thumbnail")
                    text = gr.Textbox(label="Transcription", placeholder="Transcription Output", lines=10)
                # with gr.Row().style(equal_height=True):
                #     summary = gr.Textbox(label="Summary", placeholder="Summary Output", lines=5)
                #     keywords = gr.Textbox(label="Keywords", placeholder="Keywords Output", lines=5)
                with gr.Row().style(equal_height=True):
                    btn = gr.Button("Get video insights")  # Updated button label
                btn.click(transcribe_audio, inputs=[audio_file], outputs=[text])
                # link.change(gio.populate_metadata, inputs=[link], outputs=[img, title])

demo.launch()

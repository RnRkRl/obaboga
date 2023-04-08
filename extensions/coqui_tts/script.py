import time
from pathlib import Path
from modules import chat, shared
from modules.html_generator import chat_html_wrapper

import gradio as gr
from TTS.api import TTS


# Running a multi-speaker and multilingual model
params = {
    'activate': True,
    'speaker': 'en_49',
    'language': 'en',
    'model_id': 'tts_models/en/ek1/tacotron2',
    'sample_rate': 48000,
    'device': 'cpu',
    'show_text': True,
    'autoplay': True,
    'voice_pitch': 'medium',
    'voice_speed': 'medium',
}

current_params = params.copy()
models = [
    'tts_models/en/ek1/tacotron2',
    'tts_models/en/ljspeech/tacotron2-DDC',
    'tts_models/en/ljspeech/tacotron2-DDC_ph',
    'tts_models/en/ljspeech/glow-tts',
    'tts_models/en/ljspeech/speedy-speech',
    'tts_models/en/ljspeech/tacotron2-DCA',
    'tts_models/en/ljspeech/vits',
    'tts_models/en/ljspeech/vits--neon',
    'tts_models/en/ljspeech/fast_pitch',
    'tts_models/en/ljspeech/overflow',
    'tts_models/en/ljspeech/neural_hmm',
    'tts_models/en/vctk/vits',
    'tts_models/en/vctk/fast_pitch',
    'tts_models/en/sam/tacotron-DDC',
    'tts_models/en/blizzard2013/capacitron-t2-c50',
    'tts_models/en/blizzard2013/capacitron-t2-c150_v2'
]


def load_model():
    # Init TTS
    tts = TTS(params['model_id'])
    temp_speaker = tts.speakers if tts.speakers is not None else []
    temp_speaker = params['speaker'] if params['speaker'] in temp_speaker else temp_speaker[0] if len(temp_speaker) > 0 else None

    temp_language = tts.languages if tts.languages is not None else []
    temp_language = params['language'] if params['language'] in temp_language else temp_language[0] if len(temp_language) > 0 else None

    return tts, temp_speaker, temp_language


model, speaker, language = load_model()


def remove_tts_from_history(name1, name2, mode):
    for i, entry in enumerate(shared.history['internal']):
        shared.history['visible'][i] = [shared.history['visible'][i][0], entry[1]]
    return chat_html_wrapper(shared.history['visible'], name1, name2, mode)


def toggle_text_in_history(name1, name2, mode):
    for i, entry in enumerate(shared.history['visible']):
        visible_reply = entry[1]
        if visible_reply.startswith('<audio'):
            if params['show_text']:
                reply = shared.history['internal'][i][1]
                shared.history['visible'][i] = [shared.history['visible'][i][0], f"{visible_reply.split('</audio>')[0]}</audio>\n\n{reply}"]
            else:
                shared.history['visible'][i] = [shared.history['visible'][i][0], f"{visible_reply.split('</audio>')[0]}</audio>"]
    return chat_html_wrapper(shared.history['visible'], name1, name2, mode)


def input_modifier(string):
    """
    This function is applied to your text inputs before
    they are fed into the model.
    """

    # Remove autoplay from the last reply
    if shared.is_chat() and len(shared.history['internal']) > 0:
        shared.history['visible'][-1] = [shared.history['visible'][-1][0], shared.history['visible'][-1][1].replace('controls autoplay>', 'controls>')]

    shared.processing_message = "*Is recording a voice message...*"
    shared.args.no_stream = True  # Disable streaming cause otherwise the audio output will stutter and begin anew every time the message is being updated
    return string


def output_modifier(string):
    """
    This function is applied to the model outputs.
    """

    global model, speaker, language, current_params, streaming_state

    for i in params:
        if params[i] != current_params[i]:
            model, speaker, language = load_model()
            current_params = params.copy()
            break

    if not current_params['activate']:
        return string

    original_string = string
    # string = tts_preprocessor.preprocess(string)

    if string == '':
        string = '*Empty reply, try regenerating*'
    else:
        output_file = Path(f'extensions/coqui_tts/outputs/{shared.character}_{int(time.time())}.wav')
        model.tts_to_file(text=string, speaker=speaker, language=language, file_path=str(output_file))

        autoplay = 'autoplay' if current_params['autoplay'] else ''
        string = f'<audio src="file/{output_file.as_posix()}" controls {autoplay}></audio>'
        if params['show_text']:
            string += f'\n\n{original_string}'

    shared.processing_message = "*Is typing...*"
    shared.args.no_stream = streaming_state  # restore the streaming option to the previous value
    return string


def bot_prefix_modifier(string):
    """
    This function is only applied in chat mode. It modifies
    the prefix text for the Bot and can be used to bias its
    behavior.
    """

    return string


def setup():
    global model, speaker, language
    model, speaker, language = load_model()


def ui():
    # Gradio elements
    with gr.Accordion("Coqui AI TTS"):
        with gr.Row():
            activate = gr.Checkbox(value=params['activate'], label='Activate TTS')
            autoplay = gr.Checkbox(value=params['autoplay'], label='Play TTS automatically')

        show_text = gr.Checkbox(value=params['show_text'], label='Show message text under audio player')
        model_dropdown = gr.Dropdown(value=params['model_id'], choices=models, label='Model')
        voice = gr.Dropdown(value=params['speaker'], choices=model.speakers if model.speakers is not None else [], label='Speaker')
        lang = gr.Dropdown(value=params['language'], choices=model.languages if model.languages is not None else [], label='Language')

        with gr.Row():
            convert = gr.Button('Permanently replace audios with the message texts')
            convert_cancel = gr.Button('Cancel', visible=False)
            convert_confirm = gr.Button('Confirm (cannot be undone)', variant="stop", visible=False)

    # Convert history with confirmation
    convert_arr = [convert_confirm, convert, convert_cancel]
    convert.click(lambda: [gr.update(visible=True), gr.update(visible=False), gr.update(visible=True)], None, convert_arr)
    convert_confirm.click(lambda: [gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)], None, convert_arr)
    convert_confirm.click(remove_tts_from_history, [shared.gradio[k] for k in ['name1', 'name2', 'Chat mode']], shared.gradio['display'])
    convert_confirm.click(lambda: chat.save_history(timestamp=False), [], [], show_progress=False)
    convert_cancel.click(lambda: [gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)], None, convert_arr)

    # Toggle message text in history
    show_text.change(lambda x: params.update({"show_text": x}), show_text, None)
    show_text.change(toggle_text_in_history, [shared.gradio[k] for k in ['name1', 'name2', 'Chat mode']], shared.gradio['display'])
    show_text.change(lambda: chat.save_history(timestamp=False), [], [], show_progress=False)

    # Event functions to update the parameters in the backend
    activate.change(lambda x: params.update({"activate": x}), activate, None)
    autoplay.change(lambda x: params.update({"autoplay": x}), autoplay, None)
    model_dropdown.change(lambda x: params.update({"model_id": x}), model_dropdown, None)
    voice.change(lambda x: params.update({"speaker": x}), voice, None)
    lang.change(lambda x: params.update({"language": x}), lang, None)

# Componentes externos e atribuições

O código deste wrapper é MIT. Dependências, modelos e datasets conservam suas licenças próprias; não são relicenciados por este repositório. Este repositório não redistribui pesos ou gravações.

- **OpenVoice V1/V2**, MyShell / MIT, [repositório](https://github.com/myshell-ai/OpenVoice), [licença original](https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE), [modelos V2 oficiais](https://huggingface.co/myshell-ai/OpenVoiceV2). Código instalado separadamente, na revisão `74a1d147b17a8c3092dd5430504bd83ef6c7eb23`. A classe de compatibilidade usa a arquitetura e os métodos de extração/conversão originais, sem copiar o código do modelo para este repositório.
- **Piper 1.8.0**, Open Home Foundation, [código e licença GPL-3.0](https://github.com/OHF-Voice/piper1-gpl). Executado exclusivamente como programa externo em outro ambiente Python. Não é incorporado nem distribuído no pacote deste wrapper. Redistribuir o Piper ou um bundle que o inclua exige cumprir a GPL e a licença de seus componentes, inclusive eSpeak NG.
- **Piper Faber medium, PT-BR**: [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD), dataset indicado como CC0. A base foi ajustada a partir de Lessac medium. A licença individual e os avisos do catálogo de modelos devem ser preservados.
- **Piper LJ Speech medium, inglês dos EUA**: [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD), dataset LJ Speech de domínio público, modelo treinado por Bryce Beattie. O instalador salva o model card.
- **Piper Siwis medium, francês**, opcional: [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD), corpus SIWIS da Universidade de Edimburgo, CC-BY 4.0. Preserve a atribuição ao utilizar ou redistribuir material sujeito a essa licença.
- **Silero VAD**, [repositório e licença MIT](https://github.com/snakers4/silero-vad), usado para segmentação de fala local, com modelo incluído no pacote.
- **PyTorch / torchaudio**, **NumPy**, **SciPy**, **librosa** e **SoundFile**: dependências instaladas pelo gerenciador Python, com suas licenças e avisos originais.
- **FFmpeg**, executável externo fornecido pelo usuário; licença depende do build e codecs. Não distribuído aqui.

Autorização para clonar uma pessoa ou reutilizar uma voz gerada por outro serviço deve ser obtida separadamente. A licença do software não concede direitos sobre a identidade vocal nem sobre gravações de terceiros.

Referência acadêmica: Qin, Zengyi; Zhao, Wenliang; Yu, Xumin; Sun, Xin. *OpenVoice: Versatile Instant Voice Cloning*, 2023. [arXiv:2312.01479](https://arxiv.org/abs/2312.01479).

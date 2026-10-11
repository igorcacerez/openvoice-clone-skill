---
name: openvoice-clone
description: Cadastre e reutilize vozes autorizadas em uma biblioteca local persistente para narrar textos e arquivos TXT com OpenVoice e TTS local, especialmente em português brasileiro. Use para clonagem de timbre, gerenciamento de perfis ou geração local de WAV/MP3 com uma voz salva.
---

# OpenVoice Clone

Execute o código instalado, não apenas forneça instruções. O perfil e a configuração são globais por usuário; o projeto atual não define a biblioteca.

## Encontrar a instalação

Use `scripts/run.py` desta skill com um Python disponível (3.10/3.11 recomendado). Ele localiza a configuração em `%APPDATA%/openvoice-clone/config.json` no Windows ou `~/.config/openvoice-clone/config.json` no Linux, e executa a CLI no ambiente isolado. `OPENVOICE_CONFIG` pode definir outra configuração. No Windows já instalado, a CLI está sob o `root` configurado, em `.venv/Scripts/openvoice-skill.exe`.

Execute `doctor` se houver dúvida sobre a instalação; `doctor --load-models` também verifica o conversor real. Não reinstale nem baixe modelos a cada chamada.

## Cadastro e gerenciamento

Antes de cadastrar, atualizar ou importar uma voz, tenha confirmação explícita do usuário de que possui autorização para cloná-la e reutilizá-la. Ter um arquivo ou uma voz disponível em um serviço não basta. Não transmita referências ou embeddings a serviços externos. Use `--consent-confirmed` somente após confirmação no contexto atual ou autorização explícita anterior aplicável à mesma voz.

Localize o caminho real do áudio anexado e execute:

```text
voices add --name "Nome" --audio "caminho/gravacao.wav" --consent-confirmed
voices list
voices info "Nome"
voices preview "Nome"
```

O cadastro valida fala, remove silêncios e salva uma referência local e embedding NumPy. Avisos de ruído e checagem de locutor são heurísticos: não declare que garantem uma única pessoa ou qualidade profissional. Confira a prévia e informe os avisos relevantes.

Conflitos não sobrescrevem uma voz. Use `voices update` para trocar uma referência mantendo o identificador; revisões anteriores são preservadas. Renomeie ou exclua apenas por pedido do usuário. Exclusão move para a lixeira local; não afirme apagamento definitivo. Para importar/exportar e recuperar perfis, leia [operations.md](references/operations.md).

## Narração

Se o usuário especificar uma voz, busque por nome/ID. Se não especificar, liste as vozes e solicite a escolha quando houver mais de uma; com uma voz, use-a e informe qual foi escolhida. Se não houver voz cadastrada, solicite uma referência autorizada. Não invente perfis nem clone uma pessoa pelo nome.

```text
generate --voice "Nome" --text "Olá, este é um teste."
generate --voice "Nome" --file "roteiro.txt" --language pt-BR --output "narracao.mp3"
```

Para textos longos, use um arquivo UTF-8 em área local temporária; evite interpolar textos extensos em comandos de shell. `--format wav|mp3`, `--speed 0.5..2.0`, `--tau 0.05..1.0`, `--max-chars 260` são controles reais. `tau` é parâmetro do conversor, não emoção. Não prometa clonar sotaque, emoção ou desempenho vocal: o OpenVoice converte timbre, e pronúncia/ritmo vêm do TTS base. PT-BR usa Kokoro feminino quando configurado; Piper é a base legada. Para pedidos de ritmo calmo, use --speed 0.8 com Kokoro; ele separa frases e adiciona pausas. Outros idiomas precisam de um TTS instalado e calibrado. Não use APIs pagas como fallback sem solicitação.

A CLI retorna JSON em stdout e progresso sem texto narrado em stderr. Verifique `ok`, existência do arquivo, duração e erros antes de anunciar conclusão. Arquivo gerado não comprova qualidade: verifique a inteligibilidade com transcrição local quando disponível e apresente uma prévia para escuta. Não declare emoção ou naturalidade comprovadas apenas pelos testes. Apresente o áudio com Markdown usando o caminho absoluto: `![Narração](CAMINHO_ABSOLUTO)` e identifique-o como voz sintética. Não envie nem publique áudios sem pedido explícito. O histórico guarda hash e tamanho do texto, não seu conteúdo.

## Falhas

Erro de CUDA: tente CPU com `OPENVOICE_DEVICE=cpu`, preservando a biblioteca. Checkpoint ausente: veja a [instalação documentada](https://github.com/igorcacerez/openvoice-clone-skill). Perfil corrompido: não reutilize o embedding; restaure backup ou peça atualização autorizada. Não esconda falhas nem apresente teste sintético como prova de semelhança com uma pessoa real.

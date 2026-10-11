# OpenVoice Clone Skill

Skill para Codex que cadastra vozes autorizadas em uma biblioteca persistente e gera narrações locais em WAV ou MP3. Combina **OpenVoice V2 para conversão de timbre**, **Piper para texto em fala** e **FFmpeg para processamento/exportação**, sem consumir APIs pagas.

[OpenVoice original](https://github.com/myshell-ai/OpenVoice) é o modelo de conversão vocal. Este projeto fornece a aplicação ao redor dele: instalação isolada, CLI, armazenamento, consentimento, tratamento de áudios, geração em segmentos, integração com Codex e testes. Não treina um modelo novo e não modifica os pesos oficiais.

## Recursos

- Cadastro, listagem, consulta por nome/ID, atualização de referência, renomeação e exclusão recuperável.
- SQLite para metadados e histórico; WAV e embedding NumPy persistentes por voz/revisão.
- Validação com FFprobe, conversão mono, Silero VAD e remoção de silêncios para cadastro.
- Verificação de saturação, ruído e inconsistência entre embeddings dos segmentos, com limitações explícitas.
- PT-BR com Piper Faber medium; inglês dos EUA com LJ Speech medium. Francês Siwis opcional.
- Segmentação de textos longos, conversão de cada trecho, pausas, fades curtos e normalização de volume.
- WAV/MP3, velocidade, parâmetro `tau` do conversor e diretório de saída configurável.
- Importação/exportação de perfis ZIP com checksums e embeddings sem pickle.
- Configuração global por usuário e execução independente do projeto atual.

O OpenVoice **converte o timbre**, mas **não replica automaticamente sotaque ou emoção**. Pronúncia e prosódia são controladas pela voz base. A qualidade depende do áudio de referência e da adequação do TTS; compare uma prévia antes de usar a narração final.

## Requisitos

- Windows 11 ou Linux; Python **3.10/3.11**, recomendado 3.11; Git, `uv`, FFmpeg e FFprobe no PATH.
- CPU funciona; GPU NVIDIA com driver compatível acelera o conversor. A instalação CUDA usa PyTorch **2.5.1 + CUDA 11.8**; não exige instalar o toolkit CUDA global para inferência.
- Recomenda-se 8 GB ou mais de RAM e alguns GB livres para ambientes e cache. O download CUDA do PyTorch é grande. A instalação desta máquina foi verificada em GTX 1650, 4 GB de VRAM; isso não garante que todo comprimento de segmento caiba em qualquer GPU.
- Modelos baixados uma vez. Após instalação, cadastro e geração usam arquivos locais, sem enviar gravações ou texto à nuvem.

### Windows

Instale os requisitos se ainda não estiverem presentes:

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Gyan.FFmpeg -e
```

Abra um terminal novo para atualizar o PATH, então:

```powershell
git clone https://github.com/igorcacerez/openvoice-clone-skill.git
cd openvoice-clone-skill
uv run --python 3.11 --no-project scripts/install.py `
  --root E:\VideoEditor\Apps\OpenVoice `
  --models E:\VideoEditor\Models\OpenVoice `
  --data E:\VideoEditor\Media\OpenVoiceLibrary `
  --exports E:\VideoEditor\Exports\OpenVoice `
  --cache E:\VideoEditor\Cache\OpenVoice `
  --language pt-BR --language en-US
```

O instalador cria dois ambientes isolados: `.venv` para OpenVoice e `piper-venv` para Piper. Mantém o código do OpenVoice em `repo` na revisão fixada. Não substitui Python ou bibliotecas globais. Repetir a instalação com a mesma biblioteca preserva os perfis; se houver outra revisão ou biblioteca configurada, o instalador interrompe para evitar mudanças implícitas.

Para CPU, acrescente `--device cpu`. Depois de instalar:

```powershell
E:\VideoEditor\Apps\OpenVoice\.venv\Scripts\openvoice-skill.exe doctor --load-models
```

Nesta máquina também existe `E:\VideoEditor\Scripts\openvoice-skill.cmd` para execução interna pelo Codex. Você pode usar os pedidos em linguagem natural descritos abaixo, sem precisar executar comandos.

### Linux

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg
# Instale uv pelo método oficial da Astral, se necessário.
git clone https://github.com/igorcacerez/openvoice-clone-skill.git
cd openvoice-clone-skill
uv run --python 3.11 --no-project scripts/install.py --device cpu --language pt-BR --language en-US
~/.local/share/openvoice/.venv/bin/openvoice-skill doctor --load-models
```

Linux é um caminho previsto pelo instalador, mas a inferência desta instalação foi verificada no Windows nativo. Não é necessário WSL2 ou Docker aqui. Para uma máquina Windows incompatível, use WSL2 com o procedimento Linux e instale o runtime e biblioteca dentro do sistema Linux; execute o runner pelo WSL e não misture os executáveis Windows/Linux. Nenhuma imagem Docker é fornecida ou declarada validada por este projeto.

### Modelos, versões e reprodutibilidade

O instalador chama `scripts/setup_models.py`; não baixa pesos a cada geração.

```powershell
python scripts/setup_models.py --models E:\VideoEditor\Models\OpenVoice --language pt-BR --language en-US
```

O V2 usa o modelo oficial `myshell-ai/OpenVoiceV2` na revisão `f36e7edfe1684461a8343844af60babc2efbb727`. O link S3 antigo da documentação original retornou HTTP 404 durante a instalação; o download usa o repositório oficial da mesma organização no Hugging Face. Os modelos Piper usam a revisão `c10ece1aade47bb51c153c893d14e5bf8e5b7117` de `rhasspy/piper-voices`. Pesos principais têm SHA256 esperado fixado; o conversor confere seu checksum antes de carregar. Um manifesto local registra os hashes.

`requirements-windows-cu118.lock` e `requirements-piper-windows.lock` registram as dependências exatas da instalação validada. Para restaurar o ambiente Windows com o lock, use `uv pip install --python CAMINHO_PYTHON -r requirements-windows-cu118.lock --extra-index-url https://download.pytorch.org/whl/cu118`; instale o projeto com `--no-deps -e .`. O lock Windows não deve ser usado cegamente em outro sistema; o instalador fixa as dependências diretas e escolhe o wheel PyTorch do sistema.

V1 é opcional: `setup_models.py --with-v1`, seguido de `version: "v1"` na configuração. Embeddings V1 e V2 não são intercambiáveis: use biblioteca separada e cadastre novamente as referências autorizadas. A inferência V1 não faz parte do caminho validado inicialmente.

## Configuração

O arquivo global fica em `%APPDATA%\openvoice-clone\config.json` no Windows e `~/.config/openvoice-clone/config.json` no Linux. Consulte `config.example.json`.

- `OPENVOICE_CONFIG`: arquivo de configuração alternativo.
- `OPENVOICE_HOME`, `OPENVOICE_DATA`, `OPENVOICE_MODELS`, `OPENVOICE_EXPORTS`, `OPENVOICE_CACHE`, `OPENVOICE_REPO`: substituem diretórios.
- `OPENVOICE_DEVICE=cpu` ou `cuda:0`: escolhe o dispositivo.
- `piper_models`: mapeamento de idiomas para modelos ONNX locais.
- `threads`: threads CPU; padrão 4.

Idiomas instalados aparecem em `doctor`. Para francês opcional, baixe `--language fr-FR` e acrescente o caminho retornado a `piper_models`, preservando os idiomas existentes. A calibração está implementada para os idiomas listados em `CALIBRATION`. Outros modelos Piper podem ser integrados por configuração e texto de calibração adequado; isso exige teste real. Espanhol, chinês, japonês e coreano do pipeline nativo MeloTTS não estão instalados por este projeto. A compatibilidade do conversor com um idioma não substitui um TTS funcional nesse idioma.

## Utilização pela CLI

Nos exemplos, `openvoice-skill` representa o executável dentro do ambiente instalado. Você não precisa ativar o ambiente se usar o caminho completo.

```text
openvoice-skill doctor
openvoice-skill voices add --name "Minha voz" --audio "referencia.wav" --consent-confirmed
openvoice-skill voices list
openvoice-skill voices info "Minha voz"
openvoice-skill voices preview "Minha voz"
openvoice-skill voices rename "Minha voz" "Voz principal"
openvoice-skill voices update "Voz principal" --audio "referencia-nova.wav" --consent-confirmed
openvoice-skill voices delete "Voz principal"
```

`--consent-confirmed` registra a declaração de autorização para usar a voz. O agente deve obter essa confirmação antes de passar a opção. Este software não comprova direitos ou identidade. Referências devem conter um único locutor, fala limpa e autorização; recomendado 15–60 segundos, aceitos 4 segundos a 10 minutos. No máximo 120 segundos de fala são usados para o embedding, sem guardar o arquivo original completo.

### Gerar narração

```text
openvoice-skill generate --voice "Minha voz" --text "Olá, esta é uma narração em português brasileiro."
openvoice-skill generate --voice "Minha voz" --file "roteiro.txt" --language pt-BR --output "narracao.mp3"
openvoice-skill generate --voice "Minha voz" --file "aula.txt" --format wav --speed 1.05
openvoice-skill generate --voice "Minha voz" --text "This is an English test." --language en-US
openvoice-skill history --limit 10
```

Arquivos TXT devem ser UTF-8; UTF-8 com BOM é aceito. Textos são divididos por sentenças e espaços, respeitando por padrão 260 caracteres por trecho. `--max-chars` permite reduzir isso em hardware limitado. Palavras não são cortadas ao meio; um token excessivamente longo gera erro. O pipeline carrega o conversor uma vez por chamada, Piper uma vez para o lote e reutiliza o embedding base em cache com hash dos modelos. União é escrita em disco, sem concatenar a narração longa inteira na RAM.

`--speed` aceita 0.5–2.0 e altera a duração de fonemas no Piper. `--tau` aceita 0.05–1.0, padrão 0.3; é parâmetro real da conversão, não controle de emoção. Não há controle de gênero, emoção ou sotaque nesta aplicação.

Sem `--output`, o nome é automático no diretório de exports. Arquivos existentes nunca são sobrescritos. WAV sai como PCM 16 bits, mono, 44.1 kHz; MP3 sai em 192 kbps. Volume usa `loudnorm` com alvo -18 LUFS, teto -1.5 dBTP e LRA 11; por ser um processamento de passagem única, não promete medida final exata em todo conteúdo. Os arquivos têm identificação de áudio sintético em metadados e JSON adjacente. A marca d'água neural opcional `wavmark` não é instalada.

### Resultados e erros

Todos os comandos retornam JSON com `ok` e `result`, ou `ok: false` e `error`. Progresso vai para stderr sem o texto narrado. Saída 0 significa sucesso, 1 significa doctor com requisitos ausentes, 2 erro de entrada/arquivo, 3 erro de processamento e 130 interrupção. Consulte [troubleshooting](references/troubleshooting.md).

## Integração com Codex

O instalador copia `SKILL.md`, o runner e as referências para `$CODEX_HOME/skills/openvoice-clone`, ou `~/.codex/skills/openvoice-clone`. A estrutura segue o formato local de skills com frontmatter `name`/`description` e metadados de interface em `agents/openai.yaml`. Reinicie o Codex para atualizar sua lista de skills.

Exemplos de mensagens:

- “Use a skill openvoice-clone e cadastre este áudio como Minha voz. Tenho autorização para cloná-la e reutilizá-la.”
- “Liste minhas vozes cadastradas.”
- “Use a voz Minha voz para narrar o texto abaixo: …”
- “Gere um MP3 com a voz Minha voz a partir deste roteiro.”
- “Renomeie a voz Minha voz para Voz principal.”
- “Exclua o perfil Voz principal da biblioteca.”

Se o usuário não indicar uma voz, o agente consulta a biblioteca e solicita a escolha quando houver várias. Não precisa reenviar uma gravação já cadastrada. O runner usa a configuração global e funciona a partir de outro diretório; modelos e perfis permanecem fora da skill para sobreviver a suas atualizações.

## Armazenamento, backup e privacidade

Na instalação configurada em E:, os perfis ficam em `E:\VideoEditor\Media\OpenVoiceLibrary`, fora deste repositório. Cada perfil tem UUID, nome, idioma, timestamps, declaração de consentimento, métricas, hashes, referência WAV e embedding `.npy` carregado com `allow_pickle=False`. O SQLite seleciona a revisão ativa. Atualizar uma referência cria outra revisão; não remove a anterior.

Gerações recebem histórico com hash do texto, tamanho, caminho, status e duração; **não guarda o texto integral**. O áudio naturalmente contém a fala. Arquivos privados não devem entrar em Git, logs públicos ou relatórios de CI. Exclusão retira o perfil da biblioteca e move suas revisões à lixeira local; isso é recuperável e não é apagamento definitivo.

```text
openvoice-skill voices export "Minha voz" --output "backup-privado.zip"
openvoice-skill voices import "backup-privado.zip" --name "Voz restaurada" --consent-confirmed
```

Faça backup completo copiando o diretório `data` **com os processos de geração fechados**, incluindo arquivos SQLite auxiliares se existirem. Restaure o conjunto integral e configure `OPENVOICE_DATA` para essa cópia, ou use ZIPs de perfis. ZIPs contêm gravações e embeddings: mantenha-os privados. Veja [operações](references/operations.md).

## Testes

```powershell
# Testes leves: não baixam nem carregam modelos.
python -m pytest -m "not integration" -q
ruff check src scripts tests

# Inferência local real: usa voz sintética e biblioteca isolada de teste.
$env:OPENVOICE_TEST_MODELS = '1'
python -m pytest -m integration -q -s
```

O teste de inferência sintetiza uma referência com Piper, extrai o embedding V2, cadastra e recupera um perfil, gera WAV e texto longo em MP3, verifica arquivos e duração, rejeita sobrescrita e arquivo inválido, testa export/import/rename/delete e, se instalado, geração em inglês. Não usa gravações pessoais. Testes leves cobrem persistência, conflitos, checksums, recuperação, consentimento, ZIP inseguro, pickle recusado e preservação de texto segmentado.

O template [ci-workflow.yml](references/ci-workflow.yml) executa somente os testes leves, sem Torch ou checkpoints. Não há workflow ativo nesta publicação: a autenticação GitHub disponível recusou arquivos em `.github/workflows` por falta de escopo `workflow`. Para habilitar Actions com uma credencial autorizada, copie esse template para `.github/workflows/tests.yml` e envie o commit. Nenhum resultado de CI remota é declarado como executado.

Resultados verificados da instalação são documentados em [validation.md](references/validation.md), sem áudios ou dados privados.

## Fluxo completo

Após instalar e obter uma gravação autorizada:

1. Execute `doctor --load-models` e confira `ok`.
2. Cadastre com `voices add --name "Minha voz" --audio "referencia.wav" --consent-confirmed`.
3. Confirme o perfil com `voices info "Minha voz"`.
4. Reinicie o processo e execute `voices list` para verificar a persistência.
5. Gere a prévia com `voices preview "Minha voz"` e escute.
6. Gere um roteiro TXT com `generate --voice "Minha voz" --file "roteiro.txt" --output "narracao.mp3"`.
7. Confira o arquivo final, a duração e a qualidade perceptiva antes de publicar por sua iniciativa.

## Limitações

Não há garantia de semelhança perfeita, naturalidade profissional ou sotaque idêntico. A checagem de múltiplos locutores usa consistência de embeddings; é heurística e pode perder locutores semelhantes ou sinalizar variações do mesmo locutor. A métrica de ruído também é aproximada. Não implementa diarização completa, restauração de gravações ruins nem remove música de fundo automaticamente.

Operações que alteram/geram perfis são serializadas por locks para proteger as referências. Cada chamada da CLI carrega seu próprio conversor; ele é reutilizado entre segmentos dentro dessa chamada. Interrupções abruptas podem deixar revisões de staging ou geração com status `running`; os perfis já confirmados não são substituídos. Sem daemon de modelos residente nesta versão.

Veja [NOTICE.md](NOTICE.md) para licenças e atribuições. O wrapper é MIT; dependências externas conservam suas próprias licenças.

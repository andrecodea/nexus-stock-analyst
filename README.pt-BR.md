# Nexus Financial Agent

Instruções rápidas e notas para desenvolvedores (Português).

Pré-requisitos
- Node.js (frontend)
- Python 3.10+ (backend)

Configuração
1. Backend
   - Crie um ambiente virtual e instale dependências:
     ```powershell
     cd backend
     python -m venv .venv
     . .venv\Scripts\Activate.ps1   # PowerShell (Windows)
     pip install -r requirements.txt || pip install .
     ```
   - Copie o exemplo de env e preencha as chaves localmente:
     ```bash
     cp ../.env.example .env
     # editar backend/.env com as chaves reais (NÃO COMMITAR)
     ```

2. Frontend
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Segurança e histórico Git
- Arquivo `backend/.env` continha chaves sensíveis e o histórico do repositório foi reescrito para removê-las. Você deve rotacionar/trocar qualquer chave que tenha sido exposta.
- Devido à reescrita do histórico, colaboradores devem clonar novamente o repositório para evitar conflitos:
  ```bash
  git clone https://github.com/andrecodea/nexus-financial-analyst.git
  ```

Observações
- Nunca comite arquivos `.env` ou outros arquivos com segredos. Use `.
.env.example` como modelo.
- Posso executar uma varredura mais profunda por segredos ou gerar instruções para rotacionar chaves, se desejar.

Aviso importante: Arquivo de ambiente
- Use `backend/.env.example` como o modelo canônico para variáveis de ambiente. NÃO comite `backend/.env` ou qualquer arquivo com segredos reais.
- O repositório teve o histórico reescrito para remover um `.env` que foi comitado anteriormente; se você suspeita que chaves foram expostas, rotacione-as imediatamente.
- Após a reescrita do histórico, colaboradores devem clonar novamente o repositório para evitar conflitos:
  ```bash
  git clone https://github.com/andrecodea/nexus-financial-analyst.git
  ```

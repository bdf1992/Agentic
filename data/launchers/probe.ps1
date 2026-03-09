$prompt = Get-Content -Path 'C:\Users\bdf19\OneDrive\Desktop\Rift Realms\Agentic\data\prompts\probe.txt' -Raw -Encoding UTF8
claude --system-prompt $prompt --model opus --allowedTools Bash,Read,Write,Edit,Grep,Glob --permission-mode acceptEdits --mcp-config "C:\Users\bdf19\OneDrive\Desktop\Rift Realms\Agentic\.mcp.json"

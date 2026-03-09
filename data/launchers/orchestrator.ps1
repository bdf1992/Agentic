$prompt = Get-Content -Path 'C:\Users\bdf19\OneDrive\Desktop\Rift Realms\Agentic\data\prompts\orchestrator.txt' -Raw -Encoding UTF8
claude --system-prompt $prompt --model opus --allowedTools Bash,Read,Grep,Glob --permission-mode acceptEdits --add-dir "C:\Users\bdf19\OneDrive\Desktop\Rift Realms\system3" --mcp-config "C:\Users\bdf19\OneDrive\Desktop\Rift Realms\Agentic\.mcp.json"

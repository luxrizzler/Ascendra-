"""
AI Academy curriculum data.
Paths -> Modules -> Lessons. Each lesson has swipeable cards + a quiz question.
"""

AI_MODELS = [
    {
        "id": "gpt-5-2",
        "name": "GPT-5.2",
        "provider": "OpenAI",
        "category": "Text",
        "color": "#10A37F",
        "tagline": "The most capable general reasoning model.",
        "description": "OpenAI's flagship 2026 reasoning model. Best for complex problem solving, agents, coding and multi-step planning.",
        "use_cases": ["Agents & automation", "Advanced coding", "Long-form reasoning", "Research assistants"],
        "strengths": "Best-in-class reasoning, tool use, long context.",
        "pricing_hint": "Premium",
    },
    {
        "id": "claude-sonnet-4-5",
        "name": "Claude Sonnet 4.5",
        "provider": "Anthropic",
        "category": "Text",
        "color": "#D97757",
        "tagline": "Thoughtful, safe, and great at writing.",
        "description": "Anthropic's balanced workhorse. Outstanding for nuanced writing, analysis, and conversational agents.",
        "use_cases": ["Writing & editing", "Customer support", "Code review", "Document analysis"],
        "strengths": "Long context, careful tone, excellent code.",
        "pricing_hint": "Mid",
    },
    {
        "id": "claude-opus-4-5",
        "name": "Claude Opus 4.5",
        "provider": "Anthropic",
        "category": "Text",
        "color": "#B45309",
        "tagline": "Anthropic's most powerful brain.",
        "description": "When you need the absolute deepest thinking — research, strategy, complex synthesis.",
        "use_cases": ["Strategy work", "Research synthesis", "Legal analysis", "PhD-level reasoning"],
        "strengths": "Deep reasoning, nuance, judgment.",
        "pricing_hint": "Premium",
    },
    {
        "id": "claude-haiku-4-5",
        "name": "Claude Haiku 4.5",
        "provider": "Anthropic",
        "category": "Text",
        "color": "#A16207",
        "tagline": "Fast, cheap, surprisingly smart.",
        "description": "Lightning-fast small model. Perfect for classification, summarization, and high-volume tasks.",
        "use_cases": ["Classification", "Summaries", "Chat at scale", "RAG"],
        "strengths": "Speed, cost, reliability.",
        "pricing_hint": "Low",
    },
    {
        "id": "gemini-3-pro",
        "name": "Gemini 3 Pro",
        "provider": "Google",
        "category": "Text",
        "color": "#4285F4",
        "tagline": "Multimodal powerhouse with massive context.",
        "description": "Google's flagship. Native multimodal — text, image, audio, and video understanding in one model.",
        "use_cases": ["Multimodal analysis", "Long documents", "Video understanding", "Data extraction"],
        "strengths": "Multimodality + 1M token context.",
        "pricing_hint": "Mid",
    },
    {
        "id": "gemini-3-flash",
        "name": "Gemini 3 Flash",
        "provider": "Google",
        "category": "Text",
        "color": "#34A853",
        "tagline": "Cheap, fast, multimodal.",
        "description": "The everyday workhorse from Google. Great for production apps that need speed and low cost.",
        "use_cases": ["Production APIs", "Chatbots", "Image Q&A", "Realtime analysis"],
        "strengths": "Cost-performance ratio.",
        "pricing_hint": "Low",
    },
    {
        "id": "nano-banana",
        "name": "Nano Banana",
        "provider": "Google",
        "category": "Image",
        "color": "#FBBC04",
        "tagline": "Gemini's image-gen model. Edits images conversationally.",
        "description": "State-of-the-art image generation and editing. Talk to it like a designer.",
        "use_cases": ["Product mockups", "Marketing visuals", "Photo editing", "Brand assets"],
        "strengths": "Conversational image editing.",
        "pricing_hint": "Low",
    },
    {
        "id": "gpt-image-1",
        "name": "GPT Image 1",
        "provider": "OpenAI",
        "category": "Image",
        "color": "#10A37F",
        "tagline": "OpenAI's photorealistic image model.",
        "description": "Powerful image generation with strong prompt adherence and text rendering.",
        "use_cases": ["Marketing", "Illustration", "UX mockups", "Editorial"],
        "strengths": "Prompt adherence, text in images.",
        "pricing_hint": "Mid",
    },
    {
        "id": "sora-2",
        "name": "Sora 2",
        "provider": "OpenAI",
        "category": "Video",
        "color": "#000000",
        "tagline": "Cinematic AI video, prompt-to-clip.",
        "description": "Generate up to a minute of stunning video from a prompt. Best-in-class realism.",
        "use_cases": ["Ad creative", "Storyboards", "Social content", "Pitch films"],
        "strengths": "Realism, motion coherence.",
        "pricing_hint": "Premium",
    },
    {
        "id": "veo-3",
        "name": "Veo 3",
        "provider": "Google DeepMind",
        "category": "Video",
        "color": "#1A73E8",
        "tagline": "Google's cinematic video model.",
        "description": "1080p AI video with audio. Great for product launches and creative work.",
        "use_cases": ["Cinematics", "Product demos", "Trailers"],
        "strengths": "Audio + video together.",
        "pricing_hint": "Premium",
    },
    {
        "id": "elevenlabs",
        "name": "ElevenLabs",
        "provider": "ElevenLabs",
        "category": "Audio",
        "color": "#F0F0F0",
        "tagline": "Hyper-realistic AI voices in 30+ languages.",
        "description": "Voice cloning, dubbing, and ultra-realistic text-to-speech.",
        "use_cases": ["Audiobooks", "Voiceovers", "Dubbing", "IVR"],
        "strengths": "Voice realism + emotion.",
        "pricing_hint": "Mid",
    },
    {
        "id": "whisper",
        "name": "Whisper",
        "provider": "OpenAI",
        "category": "Audio",
        "color": "#10A37F",
        "tagline": "Best-in-class speech-to-text.",
        "description": "Open-source speech recognition that just works. Supports 90+ languages.",
        "use_cases": ["Transcription", "Subtitles", "Voice agents"],
        "strengths": "Multilingual accuracy.",
        "pricing_hint": "Low",
    },
    {
        "id": "perplexity",
        "name": "Perplexity",
        "provider": "Perplexity AI",
        "category": "Search",
        "color": "#22B8CD",
        "tagline": "AI-native search with citations.",
        "description": "Real-time web search powered by LLMs. Cites every claim. The new Google for research.",
        "use_cases": ["Market research", "Fact-checking", "Live analysis"],
        "strengths": "Live web + citations.",
        "pricing_hint": "Low",
    },
    {
        "id": "midjourney",
        "name": "Midjourney v7",
        "provider": "Midjourney",
        "category": "Image",
        "color": "#9333EA",
        "tagline": "The most beautiful AI imagery.",
        "description": "The artist's choice. Best aesthetic quality, but less precise prompt control.",
        "use_cases": ["Concept art", "Mood boards", "Brand visuals", "Fine art"],
        "strengths": "Aesthetic quality.",
        "pricing_hint": "Mid",
    },
    {
        "id": "stable-diffusion",
        "name": "Stable Diffusion 4",
        "provider": "Stability AI",
        "category": "Image",
        "color": "#7C3AED",
        "tagline": "Open-source image generation.",
        "description": "Run it on your own hardware. Highly customizable with LoRAs and fine-tuning.",
        "use_cases": ["Custom pipelines", "Fine-tuned models", "Local apps"],
        "strengths": "Open weights, control.",
        "pricing_hint": "Free",
    },
    {
        "id": "runway-gen-4",
        "name": "Runway Gen-4",
        "provider": "Runway",
        "category": "Video",
        "color": "#EC4899",
        "tagline": "AI video editing studio.",
        "description": "Generate, edit, and iterate AI video clips with pro tools built around them.",
        "use_cases": ["Editing", "VFX", "Short films"],
        "strengths": "Editor + generator combo.",
        "pricing_hint": "Mid",
    },
    {
        "id": "cursor",
        "name": "Cursor",
        "provider": "Anysphere",
        "category": "Coding",
        "color": "#000000",
        "tagline": "The AI-first code editor.",
        "description": "VS Code, but with multi-file AI editing, agents, and chat built into your codebase.",
        "use_cases": ["Coding", "Refactoring", "Agentic dev"],
        "strengths": "Best AI coding UX.",
        "pricing_hint": "Mid",
    },
    {
        "id": "github-copilot",
        "name": "GitHub Copilot",
        "provider": "GitHub / OpenAI",
        "category": "Coding",
        "color": "#171515",
        "tagline": "Your pair programmer in the IDE.",
        "description": "AI autocomplete and chat in every major editor. The original AI coding tool.",
        "use_cases": ["Autocomplete", "Code chat", "Tests"],
        "strengths": "IDE ubiquity.",
        "pricing_hint": "Low",
    },
    {
        "id": "llama-4",
        "name": "Llama 4",
        "provider": "Meta",
        "category": "Text",
        "color": "#1877F2",
        "tagline": "Best open-weights LLM.",
        "description": "Meta's flagship open model. Run it anywhere, fine-tune for anything.",
        "use_cases": ["On-prem AI", "Fine-tuning", "Custom agents"],
        "strengths": "Open, customizable.",
        "pricing_hint": "Free",
    },
    {
        "id": "grok-3",
        "name": "Grok 3",
        "provider": "xAI",
        "category": "Text",
        "color": "#1DA1F2",
        "tagline": "Real-time, edgy, and integrated with X.",
        "description": "xAI's model with live access to X (Twitter) data. Great for trend analysis.",
        "use_cases": ["Trend tracking", "Social analytics"],
        "strengths": "Realtime social data.",
        "pricing_hint": "Mid",
    },
    {
        "id": "deepseek-v3",
        "name": "DeepSeek V3",
        "provider": "DeepSeek",
        "category": "Text",
        "color": "#1E40AF",
        "tagline": "Frontier-grade, ultra-cheap.",
        "description": "Surprisingly capable open-weights model from China. Punches above its price.",
        "use_cases": ["Reasoning on a budget", "Math", "Code"],
        "strengths": "Price-to-power ratio.",
        "pricing_hint": "Free",
    },
    {
        "id": "suno",
        "name": "Suno v4",
        "provider": "Suno",
        "category": "Audio",
        "color": "#F97316",
        "tagline": "Generate full songs from a prompt.",
        "description": "Lyrics, melody, vocals, instruments. Make a song in 30 seconds.",
        "use_cases": ["Jingles", "Demos", "Content music"],
        "strengths": "Full-song generation.",
        "pricing_hint": "Low",
    },
]


def _q(question, options, answer_idx, explanation):
    return {
        "question": question,
        "options": options,
        "answer_index": answer_idx,
        "explanation": explanation,
    }


def _card(title, body, kind="text"):
    return {"kind": kind, "title": title, "body": body}


PATHS = [
    {
        "id": "fundamentals",
        "title": "AI Fundamentals",
        "subtitle": "Beginner → Intermediate",
        "tagline": "Start here. Learn what AI is, how it works, and how to use it like a pro.",
        "color": "#FFB000",
        "level": "Beginner",
        "duration": "~4 hours",
        "tier": "free",
        "image": "https://images.pexels.com/photos/12623752/pexels-photo-12623752.jpeg",
        "modules": [
            {
                "id": "fundamentals-101",
                "title": "What is AI in 2026?",
                "lessons": [
                    {
                        "id": "f1l1",
                        "title": "AI vs. ML vs. LLMs",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Three words, one revolution", "Artificial Intelligence is the umbrella. Machine Learning is how machines *learn* from data. Large Language Models (LLMs) are the breakthrough that powers ChatGPT, Claude, and Gemini."),
                            _card("Why now?", "Three things collided: cheap GPUs, massive internet-scale data, and the Transformer architecture (2017). Together they made GPT-4, GPT-5, and Claude possible."),
                            _card("The 2026 landscape", "GPT-5.2, Claude Sonnet 4.5, and Gemini 3 are now multimodal — they understand text, images, audio, and video. They can reason, plan, and use tools."),
                            _card("What this means for you", "You no longer need to code to use AI. The new skill is *prompting* — knowing how to ask. That's what this app teaches you."),
                        ],
                        "quiz": _q(
                            "Which of these is the architecture that made modern LLMs possible?",
                            ["Convolutional Networks", "The Transformer", "Decision Trees", "K-Means"],
                            1,
                            "The Transformer (2017, 'Attention is All You Need') is the foundation of every modern LLM.",
                        ),
                    },
                    {
                        "id": "f1l2",
                        "title": "How LLMs actually work",
                        "duration_min": 6,
                        "xp": 60,
                        "cards": [
                            _card("Predict the next token", "An LLM's only job is predicting the next word (token). It does this brilliantly because it learned from trillions of words."),
                            _card("Training in 2 steps", "Step 1: Pre-training on the internet. Step 2: RLHF — Reinforcement Learning from Human Feedback — to make it helpful and safe."),
                            _card("Context window = working memory", "A model's *context window* is how much text it can think about at once. GPT-5.2 and Gemini 3 hit over 1M tokens. That's a whole book."),
                            _card("Why this matters", "Knowing this lets you write better prompts. More context = better answer. But irrelevant context hurts performance."),
                        ],
                        "quiz": _q(
                            "What does an LLM *fundamentally* do?",
                            ["Search the internet", "Predict the next token", "Memorize facts", "Compile code"],
                            1,
                            "LLMs are next-token predictors. Everything else is emergent behavior.",
                        ),
                    },
                    {
                        "id": "f1l3",
                        "title": "Meet the model lineup",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Reasoning models", "GPT-5.2, Claude Opus 4.5, Gemini 3 Pro — your heavy thinkers. Use these for strategy, coding, and complex tasks."),
                            _card("Fast models", "Claude Haiku, Gemini 3 Flash, GPT-5.2 mini — cheap and fast. Perfect for chatbots, classification, summaries."),
                            _card("Multimodal models", "Gemini 3 and GPT-5.2 see images and watch videos. Nano Banana and GPT Image 1 generate images. Sora 2 makes video."),
                            _card("Rule of thumb", "Start with the cheapest model that does the job. Only escalate when quality matters."),
                        ],
                        "quiz": _q(
                            "Which model is best for ultra-cheap, high-volume classification?",
                            ["Claude Opus 4.5", "Claude Haiku 4.5", "Sora 2", "Midjourney"],
                            1,
                            "Haiku is Anthropic's fastest, cheapest model — perfect for volume tasks.",
                        ),
                    },
                ],
            },
            {
                "id": "fundamentals-prompting",
                "title": "The Art of Prompting",
                "lessons": [
                    {
                        "id": "f2l1",
                        "title": "The CRISP framework",
                        "duration_min": 6,
                        "xp": 60,
                        "cards": [
                            _card("C — Context", "Tell the AI who it is and who you are. 'You are a senior copywriter. I run a SaaS startup.'"),
                            _card("R — Role & Task", "Be specific. 'Write 3 cold-email subject lines for B2B SaaS founders.'"),
                            _card("I — Input", "Give examples or source material. 'Here are 5 winning emails for reference: ...'"),
                            _card("S — Style", "Specify tone, length, format. 'Punchy, under 8 words, lowercase.'"),
                            _card("P — Polish", "Ask for variants and iterate. 'Now make them 50% more curiosity-driven.'"),
                        ],
                        "quiz": _q(
                            "What does the 'S' in CRISP stand for?",
                            ["Search", "Style", "Source", "Speed"],
                            1,
                            "Style — tone, length, and format are critical to a usable output.",
                        ),
                    },
                    {
                        "id": "f2l2",
                        "title": "Chain-of-thought prompting",
                        "duration_min": 5,
                        "xp": 60,
                        "cards": [
                            _card("Show your work", "Just adding 'Think step by step' makes LLMs dramatically better at reasoning, math, and code."),
                            _card("Why it works", "Forcing the model to lay out intermediate steps reduces hallucination. It can't 'jump to' a wrong answer."),
                            _card("Modern models do this automatically", "GPT-5.2 and Claude Sonnet 4.5 reason internally now. But for tricky problems, asking explicitly still helps."),
                        ],
                        "quiz": _q(
                            "What is the easiest way to boost a model's reasoning?",
                            ["Use more emojis", "Tell it to 'think step by step'", "Use ALL CAPS", "Use a shorter prompt"],
                            1,
                            "Classic chain-of-thought trick — still works in 2026.",
                        ),
                    },
                    {
                        "id": "f2l3",
                        "title": "Few-shot examples",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Show, don't just tell", "Give the model 2–3 examples of input → output. It will copy the pattern."),
                            _card("Why it crushes zero-shot", "LLMs are pattern matchers. Examples encode style and format better than any description."),
                            _card("Example structure", "Input: 'I love this product!' → Output: 'positive'\nInput: 'Terrible service.' → Output: 'negative'\nInput: '{user input}' → Output:"),
                        ],
                        "quiz": _q(
                            "Few-shot prompting works because LLMs are great at...",
                            ["Memorizing", "Pattern-matching", "Math", "Coding"],
                            1,
                            "Patterns. Show the AI what you want and it will copy the shape.",
                        ),
                    },
                ],
            },
            {
                "id": "fundamentals-practice",
                "title": "Your First AI Workflow",
                "lessons": [
                    {
                        "id": "f3l1",
                        "title": "Stacking models",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("One task, multiple models", "Real workflows chain models: Perplexity to research → Claude to write → Nano Banana for visuals → ElevenLabs for voiceover."),
                            _card("This is the new superpower", "You're not picking 'one AI.' You're orchestrating a team of specialists."),
                            _card("Example: a viral tweet", "Perplexity finds the trend → Claude writes 5 tweet variants → GPT Image 1 makes the meme → you post."),
                        ],
                        "quiz": _q(
                            "What's the real superpower of being AI-fluent?",
                            ["Knowing one model deeply", "Stacking multiple models in a workflow", "Coding from scratch", "Memorizing prompts"],
                            1,
                            "Stacking. Different models excel at different things — combine them.",
                        ),
                    },
                    {
                        "id": "f3l2",
                        "title": "Avoiding hallucinations",
                        "duration_min": 5,
                        "xp": 60,
                        "cards": [
                            _card("Hallucination = confident lies", "LLMs sometimes invent facts. They sound certain even when wrong. Always verify high-stakes claims."),
                            _card("3 ways to reduce them", "1. Ground in sources (Perplexity, RAG). 2. Ask for citations. 3. Use bigger reasoning models for accuracy."),
                            _card("Never trust, always verify", "For medical, legal, or financial decisions: AI gives you a draft. A human (or a source) confirms it."),
                        ],
                        "quiz": _q(
                            "What's the safest way to get sourced, citable AI answers?",
                            ["GPT-5.2 alone", "Perplexity or a RAG system", "Midjourney", "Sora 2"],
                            1,
                            "Perplexity cites sources by default. Pure LLMs make up plausible answers.",
                        ),
                    },
                ],
            },
        ],
    },
    {
        "id": "business",
        "title": "Build a Business with AI",
        "subtitle": "Entrepreneur Track",
        "tagline": "Start, run, and scale a real business with AI as your team.",
        "color": "#10B981",
        "level": "Intermediate",
        "duration": "~5 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/19826624/pexels-photo-19826624.jpeg",
        "modules": [
            {
                "id": "biz-ideate",
                "title": "Find a profitable idea",
                "lessons": [
                    {
                        "id": "b1l1",
                        "title": "The AI opportunity radar",
                        "duration_min": 6,
                        "xp": 70,
                        "cards": [
                            _card("Look for boring + manual", "The biggest AI businesses in 2026 automated boring, manual work: contracts, scheduling, bookkeeping, support."),
                            _card("3 winning patterns", "1. AI does the thing a human used to do for $50/hr. 2. AI personalizes at scale. 3. AI removes a 5-step process down to 1 click."),
                            _card("Validate with Perplexity", "Ask: 'What are the most painful, repetitive tasks in [industry] in 2026?' Read the citations. Patterns will emerge."),
                        ],
                        "quiz": _q(
                            "What's the strongest signal for an AI business idea?",
                            ["It's never been done", "It automates a boring, manual, expensive task", "It uses Sora 2", "It's free"],
                            1,
                            "Boring + expensive = where AI prints money.",
                        ),
                    },
                    {
                        "id": "b1l2",
                        "title": "Niche down to win",
                        "duration_min": 5,
                        "xp": 60,
                        "cards": [
                            _card("Generic loses", "'AI for marketing' is too broad. 'AI cold-email writer for B2B SaaS founders' wins."),
                            _card("The riches are in niches", "Specific niches = specific pain = higher willingness to pay. Charge $99/mo, not $9."),
                            _card("Use Claude to niche-storm", "Prompt: 'List 20 niches inside [broad market] where a one-person team could charge $500+/month using AI.'"),
                        ],
                        "quiz": _q(
                            "Why niche down hard?",
                            ["Easier to spell", "Specific pain = higher prices", "Fewer features needed", "Easier to hire"],
                            1,
                            "Specific pain wins. Generic loses.",
                        ),
                    },
                ],
            },
            {
                "id": "biz-build",
                "title": "Build without code",
                "lessons": [
                    {
                        "id": "b2l1",
                        "title": "Ship an MVP in a weekend",
                        "duration_min": 7,
                        "xp": 80,
                        "cards": [
                            _card("The new stack", "Emergent + Cursor + Claude lets a non-coder ship a real SaaS in 48 hours."),
                            _card("Step 1: prompt your app", "Describe your idea in plain English. The AI scaffolds the whole codebase."),
                            _card("Step 2: deploy in one click", "Modern AI platforms publish to mobile, web, and app stores. Set up payments. Charge users."),
                            _card("Step 3: iterate from real feedback", "Talk to 10 users. Feed their feedback back to the AI. Ship the next version same day."),
                        ],
                        "quiz": _q(
                            "What's the realistic timeline for an AI-built MVP?",
                            ["6 months", "A weekend to 1 week", "1 year", "Never"],
                            1,
                            "AI-native tooling collapsed it to days, not months.",
                        ),
                    },
                    {
                        "id": "b2l2",
                        "title": "Pricing & monetization",
                        "duration_min": 6,
                        "xp": 70,
                        "cards": [
                            _card("3 pricing models that work", "1. Subscription (predictable revenue). 2. Per-use (low barrier). 3. Tiered (Free → Pro → Business). This app uses #3."),
                            _card("Anchor on a high tier", "Always offer a $199+ tier. Most won't buy it — but it makes $29 feel cheap. Classic anchoring."),
                            _card("Free tier as growth engine", "Free tier = top of funnel. Limit usage so power users upgrade. Pro = paying customer. Business = highest LTV."),
                        ],
                        "quiz": _q(
                            "Why offer a high-tier plan that few people buy?",
                            ["Tax write-off", "Price anchoring makes mid-tier feel cheap", "Look prestigious", "SEO"],
                            1,
                            "Anchoring. The high tier sells the mid tier.",
                        ),
                    },
                ],
            },
            {
                "id": "biz-scale",
                "title": "Scale with AI agents",
                "lessons": [
                    {
                        "id": "b3l1",
                        "title": "Your AI team",
                        "duration_min": 6,
                        "xp": 70,
                        "cards": [
                            _card("Replace functions, not people", "One founder + 5 AI agents = a startup. Sales agent, support agent, content agent, ops agent, dev agent."),
                            _card("Tools to know", "Claude for analysis. GPT-5.2 for agentic work. Cursor for code. Nano Banana for visuals. ElevenLabs for voice support."),
                            _card("Build the AI org chart", "Map each business function. Assign an AI model and a human reviewer. The human reviews, the AI executes."),
                        ],
                        "quiz": _q(
                            "What's the right way to scale with AI in 2026?",
                            ["Hire more humans", "Build AI agents per function, humans review", "Outsource everything", "Avoid AI"],
                            1,
                            "Agents per function, humans in the loop. That's the modern small business.",
                        ),
                    },
                    {
                        "id": "b3l2",
                        "title": "Find your first 100 customers",
                        "duration_min": 6,
                        "xp": 80,
                        "cards": [
                            _card("Step 1: handcraft the first 10", "Cold DM the perfect-fit users. Onboard them yourself. Learn what they actually need."),
                            _card("Step 2: 10 → 100 with content", "Use Claude to write tweets, LinkedIn posts, blogs. Use Nano Banana for visuals. Post daily for 60 days."),
                            _card("Step 3: ads only once you have proof", "Don't burn cash on ads before product-market fit. Use organic to find it. Then pour fuel."),
                        ],
                        "quiz": _q(
                            "When should you start paid ads?",
                            ["Before launch", "After you have product-market fit signals", "Never", "After 1000 followers"],
                            1,
                            "Ads amplify what works. They don't fix what doesn't.",
                        ),
                    },
                ],
            },
        ],
    },
    {
        "id": "creators",
        "title": "AI for Creators",
        "subtitle": "Content, Design & Video",
        "tagline": "Make stunning content 10x faster — without losing your taste.",
        "color": "#EC4899",
        "level": "Intermediate",
        "duration": "~3.5 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/8672787/pexels-photo-8672787.jpeg",
        "modules": [
            {
                "id": "creators-write",
                "title": "Writing & ideation",
                "lessons": [
                    {
                        "id": "c1l1",
                        "title": "Beating the blank page",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Start with your taste, not the AI's", "Bad: 'Write a tweet.' Good: 'Here are 3 of my best tweets. Now write 5 more in this exact voice about [topic].'"),
                            _card("The voice file trick", "Save 20 of your best pieces in a doc. Paste it as context. The AI will mirror your voice."),
                            _card("Edit ruthlessly", "AI gives you a great draft. *You* make it human. Cut 30%, add one sharp opinion, ship."),
                        ],
                        "quiz": _q(
                            "What's the fastest way to make AI match your voice?",
                            ["Pay more", "Show it 10–20 of your best examples", "Use ALL CAPS", "Use Sora"],
                            1,
                            "Examples > instructions. Always.",
                        ),
                    },
                ],
            },
            {
                "id": "creators-visual",
                "title": "AI image & design",
                "lessons": [
                    {
                        "id": "c2l1",
                        "title": "Nano Banana mastery",
                        "duration_min": 6,
                        "xp": 70,
                        "cards": [
                            _card("Talk to it like a designer", "Nano Banana is conversational. 'Make it warmer.' 'Move the product left.' 'Remove the background.' It just works."),
                            _card("Reference images = gold", "Upload your brand colors, your product, a mood board. It will fuse them."),
                            _card("Iteration > perfection", "Generate 4. Pick the best. Refine. Pick again. Most pros iterate 6+ times before exporting."),
                        ],
                        "quiz": _q(
                            "What makes Nano Banana different from older image models?",
                            ["Free forever", "Conversational editing", "Higher resolution only", "It writes code"],
                            1,
                            "Conversational editing. You don't reprompt — you direct.",
                        ),
                    },
                    {
                        "id": "c2l2",
                        "title": "Choosing image models",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Midjourney = aesthetic", "Best looking output, weakest at prompt control. Use for art and mood."),
                            _card("Nano Banana = control + editing", "Best for product, marketing, and iterative work."),
                            _card("GPT Image 1 = text in images", "Crushes text rendering inside images. Use for posters and infographics."),
                        ],
                        "quiz": _q(
                            "Need a poster with readable text in the image?",
                            ["Midjourney", "GPT Image 1", "Sora 2", "Whisper"],
                            1,
                            "GPT Image 1 renders text reliably.",
                        ),
                    },
                ],
            },
            {
                "id": "creators-video",
                "title": "Audio & video",
                "lessons": [
                    {
                        "id": "c3l1",
                        "title": "Sora 2 + Veo 3 playbook",
                        "duration_min": 6,
                        "xp": 70,
                        "cards": [
                            _card("Sora 2 = realism", "Best for cinematic, photoreal clips up to 60 seconds. Use for ads and trailers."),
                            _card("Veo 3 = audio + video", "Generates synced audio. Great for product demos with voiceover baked in."),
                            _card("Pro workflow", "Storyboard in Claude → generate clips in Sora → cut in Runway → voice in ElevenLabs → music in Suno."),
                        ],
                        "quiz": _q(
                            "Need cinematic, photorealistic 30-second clips?",
                            ["Whisper", "Sora 2", "Midjourney", "Perplexity"],
                            1,
                            "Sora 2 is the gold standard for realism.",
                        ),
                    },
                    {
                        "id": "c3l2",
                        "title": "Voices that don't sound AI",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Pick the right voice library", "ElevenLabs leads on realism. Try 5 voices. Pick one that fits your brand."),
                            _card("Direction matters", "ElevenLabs lets you direct emotion. Whisper a line. Shout. Pause. Use it."),
                            _card("Always license-check", "If you clone your own voice, you're fine. Cloning someone else? Permission first. Always."),
                        ],
                        "quiz": _q(
                            "Best tool for ultra-realistic AI voiceover in 30+ languages?",
                            ["Whisper", "Sora 2", "ElevenLabs", "Suno"],
                            2,
                            "ElevenLabs is the leader in TTS realism.",
                        ),
                    },
                ],
            },
        ],
    },
    {
        "id": "productivity",
        "title": "AI for Productivity",
        "subtitle": "Work & career",
        "tagline": "Get 4 hours back every day. Use AI like the top 1% of operators.",
        "color": "#3B82F6",
        "level": "Beginner → Intermediate",
        "duration": "~3 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/18173598/pexels-photo-18173598.jpeg",
        "modules": [
            {
                "id": "prod-daily",
                "title": "Your AI daily stack",
                "lessons": [
                    {
                        "id": "p1l1",
                        "title": "The 5 daily AI moves",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("1. Inbox triage", "Claude: 'Summarize this email and draft 3 reply options — concise, friendly, firm.'"),
                            _card("2. Meeting prep", "Paste the agenda + last meeting notes. Ask for talking points and 3 risks."),
                            _card("3. Doc drafting", "Outline in 3 bullets. Ask Claude for a v1. Edit it. Ship in 20 minutes instead of 2 hours."),
                            _card("4. Research", "Perplexity for anything fact-based. Citations always."),
                            _card("5. End-of-day", "Paste today's wins + tomorrow's todos. Ask AI to draft a status update + prioritize tomorrow."),
                        ],
                        "quiz": _q(
                            "Best AI move for sourced research with citations?",
                            ["GPT-5.2 raw", "Perplexity", "Midjourney", "Sora"],
                            1,
                            "Perplexity = real-time + citations.",
                        ),
                    },
                    {
                        "id": "p1l2",
                        "title": "Calendar & email superpowers",
                        "duration_min": 5,
                        "xp": 50,
                        "cards": [
                            _card("Time-box with AI", "Paste your week's calendar. Ask Claude to find your 4 deep-work blocks. Defend them."),
                            _card("Templates beat AI from scratch", "Save your 10 most common reply templates. Ask AI to *adapt* one — much faster than writing fresh."),
                            _card("The 'no' template", "AI is great at writing graceful 'no' replies. Save your favorite and reuse it."),
                        ],
                        "quiz": _q(
                            "Best mental model for AI email replies?",
                            ["AI writes from scratch each time", "AI adapts your saved templates", "Don't use AI for email", "Voice memo only"],
                            1,
                            "Templates + adaptation = faster, more 'you'.",
                        ),
                    },
                ],
            },
            {
                "id": "prod-career",
                "title": "Career acceleration",
                "lessons": [
                    {
                        "id": "p2l1",
                        "title": "Interview prep with AI",
                        "duration_min": 5,
                        "xp": 60,
                        "cards": [
                            _card("Role-play with Claude", "Paste the job description. Tell Claude to act as the hiring manager. Run a 10-minute mock interview."),
                            _card("Get brutal feedback", "After each answer, ask: 'Rate that 1–10. Tell me what to cut, sharpen, and add.'"),
                            _card("The STAR upgrade", "Ask Claude to rewrite your stories in STAR format (Situation, Task, Action, Result). Memorable instantly."),
                        ],
                        "quiz": _q(
                            "Best AI move for interview prep?",
                            ["Memorize answers", "Mock interviews with Claude as the interviewer", "Skip prep", "Watch YouTube only"],
                            1,
                            "Active practice with feedback beats passive prep.",
                        ),
                    },
                    {
                        "id": "p2l2",
                        "title": "Learning anything 3x faster",
                        "duration_min": 5,
                        "xp": 60,
                        "cards": [
                            _card("The Feynman + AI combo", "Read a chapter. Explain it to Claude like you would to a 12-year-old. Claude tells you what you got wrong."),
                            _card("Generate flashcards", "Paste your notes. Ask: 'Make 20 spaced-repetition flashcards. Q on one side, A on the other.'"),
                            _card("Spaced practice in chat", "Tell Claude: 'Every day, quiz me on yesterday's lesson before introducing today's.' It will."),
                        ],
                        "quiz": _q(
                            "Why teach AI what you learned?",
                            ["AI gets smarter", "It exposes gaps in your understanding", "It pays you", "It writes the book"],
                            1,
                            "Teaching is testing. The gaps surface fast.",
                        ),
                    },
                ],
            },
        ],
    },
    # ─── PRO EXCLUSIVE PATHS ────────────────────────────────────────────────
    {
        "id": "prompt-mastery",
        "title": "Prompt Engineering Mastery",
        "subtitle": "Pro Exclusive · Advanced",
        "tagline": "Become the 1% who can make any model do exactly what they want.",
        "color": "#A855F7",
        "level": "Advanced",
        "duration": "~3 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/8728285/pexels-photo-8728285.jpeg",
        "modules": [
            {
                "id": "pe-advanced",
                "title": "Beyond beginner prompts",
                "lessons": [
                    {
                        "id": "pe1l1", "title": "System prompts that print money", "duration_min": 6, "xp": 80,
                        "cards": [
                            _card("Your system prompt is your asset", "A great system prompt is reusable IP. Lock it down once, run it forever."),
                            _card("The 4-part scaffold", "ROLE → CONTEXT → CONSTRAINTS → OUTPUT FORMAT. Every system prompt needs all 4."),
                            _card("Real example", "ROLE: senior copy editor. CONTEXT: B2B SaaS landing pages. CONSTRAINTS: no jargon, 8th grade level, active voice. OUTPUT: JSON with hero, sub, CTA."),
                        ],
                        "quiz": _q("What makes a system prompt reusable?", ["It's short", "It defines role + constraints + output format", "It uses ALL CAPS", "It's secret"], 1, "Structure is what makes it reusable IP."),
                    },
                    {
                        "id": "pe1l2", "title": "Self-correcting prompts", "duration_min": 6, "xp": 80,
                        "cards": [
                            _card("Tell the AI to grade itself", "Add: 'After writing, score your answer 1-10. If under 8, rewrite.' Watch quality jump."),
                            _card("The 'devil's advocate' trick", "Ask the model to critique its own output, then revise. Single-shot quality of a 5-step expert review."),
                            _card("Why this works in 2026", "Modern models (GPT-5.2, Claude 4.5) have strong self-evaluation. They know when they're weak — you just have to ask."),
                        ],
                        "quiz": _q("What does self-grading do?", ["Slows the AI down", "Forces a built-in revision pass that raises quality", "Wastes tokens", "Nothing"], 1, "The model uses its own judgment to revise itself. Free quality boost."),
                    },
                ],
            },
            {
                "id": "pe-output",
                "title": "Structured output magic",
                "lessons": [
                    {
                        "id": "pe2l1", "title": "JSON mode = production-ready", "duration_min": 5, "xp": 70,
                        "cards": [
                            _card("Tell the AI: return JSON only", "Strict JSON output is what turns LLMs from toys into APIs. GPT-5.2 and Claude 4.5 both support it natively."),
                            _card("Schema-first prompting", "Define your expected schema in the prompt. The AI fills it in. Easier than parsing free text."),
                            _card("Use case: classifier", "Input: customer review. Output: {sentiment, topics[], urgency}. Now you can pipe it into a dashboard."),
                        ],
                        "quiz": _q("Why force JSON output?", ["Aesthetic", "Production parseability", "Costs less", "Required by law"], 1, "Structured output = production-ready integrations."),
                    },
                ],
            },
        ],
    },
    {
        "id": "automation",
        "title": "AI Automation Stack",
        "subtitle": "Pro Exclusive · Workflows",
        "tagline": "Build agents and pipelines that work while you sleep.",
        "color": "#06B6D4",
        "level": "Intermediate → Advanced",
        "duration": "~4 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/16021018/pexels-photo-16021018.jpeg",
        "modules": [
            {
                "id": "auto-agents",
                "title": "Agents 101",
                "lessons": [
                    {
                        "id": "au1l1", "title": "What is an AI agent?", "duration_min": 6, "xp": 80,
                        "cards": [
                            _card("LLM + tools + loop = agent", "An agent is just an LLM that can call tools (search, code, APIs) and iterate until done."),
                            _card("Why 2026 changed everything", "GPT-5.2 and Claude 4.5 are good enough to run 10+ step plans reliably. We're past 'maybe' into 'production'."),
                            _card("The 3 modern agent patterns", "1) ReAct (reason + act). 2) Plan-then-execute. 3) Multi-agent (specialists handoff)."),
                        ],
                        "quiz": _q("An agent = LLM + ___", ["More compute", "Tools and a loop", "A bigger context window", "Multiple models"], 1, "Tools + loop. That's what makes it agentic."),
                    },
                    {
                        "id": "au1l2", "title": "MCP — the agent protocol", "duration_min": 6, "xp": 80,
                        "cards": [
                            _card("MCP = Model Context Protocol", "Anthropic's standard for plugging tools into AI agents. Like USB-C for AI."),
                            _card("Why it matters", "Once tools speak MCP, any agent (Claude, GPT, custom) can use them. No more custom integrations per model."),
                            _card("Real example", "Plug your Notion + Gmail + Linear into Claude via MCP. Now Claude can read, write, and schedule across all three."),
                        ],
                        "quiz": _q("MCP is best described as...", ["A new model", "A standard protocol for agent tools", "A payment method", "A coding language"], 1, "Protocol — the connective tissue of agents."),
                    },
                ],
            },
            {
                "id": "auto-build",
                "title": "Building your first stack",
                "lessons": [
                    {
                        "id": "au2l1", "title": "No-code automation stack", "duration_min": 6, "xp": 80,
                        "cards": [
                            _card("The 2026 stack", "Make.com or n8n (workflows) + Claude/GPT (intelligence) + Airtable/Notion (memory) = full automation."),
                            _card("Start with one painful loop", "Pick the most boring 30-min task you do daily. Automate that first. Compound from there."),
                            _card("Sample: inbox to CRM", "New email → Claude classifies → if 'lead' → push to Airtable → notify Slack. 15 minutes to build."),
                        ],
                        "quiz": _q("Where should you start automating?", ["The most exciting task", "The most painful repeated task", "The biggest task", "Anywhere"], 1, "Painful + repeated = highest leverage."),
                    },
                ],
            },
        ],
    },
    {
        "id": "code-with-ai",
        "title": "Code With AI",
        "subtitle": "Pro Exclusive · Vibe Coding",
        "tagline": "Ship full apps in days — even if you've never written a line of code.",
        "color": "#22C55E",
        "level": "Beginner → Advanced",
        "duration": "~4 hours",
        "tier": "pro",
        "image": "https://images.pexels.com/photos/4974915/pexels-photo-4974915.jpeg",
        "modules": [
            {
                "id": "code-start",
                "title": "Vibe coding fundamentals",
                "lessons": [
                    {
                        "id": "co1l1", "title": "Cursor vs Copilot vs Claude Code", "duration_min": 5, "xp": 70,
                        "cards": [
                            _card("Cursor", "Best AI-native IDE. Multi-file edits, agent mode, deep codebase understanding."),
                            _card("GitHub Copilot", "Old guard. Fast inline completion. Lives in every editor. Best as a sidekick, not lead."),
                            _card("Claude Code", "Anthropic's terminal agent. Best for autonomous, multi-step refactors and bug hunts."),
                        ],
                        "quiz": _q("Best tool for autonomous multi-step coding?", ["Cursor", "Copilot autocomplete", "Claude Code", "VS Code"], 2, "Claude Code is the terminal agent."),
                    },
                    {
                        "id": "co1l2", "title": "Prompt → working app in 1 hour", "duration_min": 7, "xp": 90,
                        "cards": [
                            _card("Step 1: describe the user", "Don't describe features. Describe who the app is for and what pain it solves. AI fills in the rest."),
                            _card("Step 2: iterate the UI before the logic", "Ship a clickable shell first. See it. Then wire it up. Avoids huge rebuilds."),
                            _card("Step 3: ship, share, fix", "Push to the cloud the same day. Hand it to a friend. Their first 'huh?' tells you what to fix."),
                        ],
                        "quiz": _q("First step in vibe coding a real app?", ["Pick a framework", "Describe the user and their pain", "Set up auth", "Buy a domain"], 1, "User first. Tech second."),
                    },
                ],
            },
        ],
    },
    # ─── BUSINESS EXCLUSIVE PATHS ───────────────────────────────────────────
    {
        "id": "startup-playbook",
        "title": "AI-First Startup Playbook",
        "subtitle": "Business Exclusive · Founder",
        "tagline": "How to start, fund, and scale a venture in the age of AI.",
        "color": "#F59E0B",
        "level": "Advanced",
        "duration": "~5 hours",
        "tier": "business",
        "image": "https://images.pexels.com/photos/8867434/pexels-photo-8867434.jpeg",
        "modules": [
            {
                "id": "sp-zero",
                "title": "From zero to first $10k",
                "lessons": [
                    {
                        "id": "sp1l1", "title": "Pre-product traction with AI", "duration_min": 7, "xp": 100,
                        "cards": [
                            _card("Find pain before building", "Use Claude to mine Reddit + X for 'I wish there was…' posts in your niche. 30 min = 50 problem statements."),
                            _card("Validate with a one-day landing page", "Build a fake-door landing in an hour. Drive 100 visitors with $50 of ads. If 5+ sign up — keep going."),
                            _card("Pre-sell before you build", "Sell the problem, not the product. If 3 people send money before launch — you have a business."),
                        ],
                        "quiz": _q("Best signal for product-market fit?", ["10k waitlist", "3 people paying before launch", "A great deck", "VC interest"], 1, "Money speaks louder than waitlists."),
                    },
                    {
                        "id": "sp1l2", "title": "The solo-founder org chart", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("You + 5 agents > you + 5 hires", "One founder + AI agents for sales, support, content, ops, and dev. 1 person, $1M ARR in 2026."),
                            _card("Pick your 'human edge'", "Be the human in the loop on the ONE function that compounds your moat. Outsource the rest to AI."),
                            _card("Hiring rule", "Don't hire until an AI agent can't do it. Even then, hire for taste, judgment, or relationships — never speed."),
                        ],
                        "quiz": _q("When do you make your first hire?", ["When you have $10k MRR", "When an AI agent literally can't do it", "When you're tired", "Never"], 1, "Replace AI only with humans who add taste, judgment, or relationships."),
                    },
                ],
            },
            {
                "id": "sp-fund",
                "title": "Fundraising in the AI era",
                "lessons": [
                    {
                        "id": "sp2l1", "title": "The new pitch deck", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("Investors changed in 2026", "VCs no longer ask 'team size?' — they ask 'agent-to-human ratio?' Higher is better."),
                            _card("Lead with the loop", "Show the AI-enabled feedback loop that compounds. Data → model → product → users → more data."),
                            _card("Defend your moat", "Saying 'we use AI' is not a moat. Saying 'we have proprietary data flowing into a private model' is."),
                        ],
                        "quiz": _q("Strongest 2026 startup moat?", ["Using GPT-5.2", "Proprietary data + private model fine-tunes", "Big team", "Slack channel"], 1, "Data flywheels eat features for breakfast."),
                    },
                ],
            },
        ],
    },
    {
        "id": "sales-engine",
        "title": "AI Sales & Marketing Engine",
        "subtitle": "Business Exclusive · Growth",
        "tagline": "Build a revenue engine that runs 24/7 on autopilot.",
        "color": "#EF4444",
        "level": "Intermediate → Advanced",
        "duration": "~4 hours",
        "tier": "business",
        "image": "https://images.pexels.com/photos/3184292/pexels-photo-3184292.jpeg",
        "modules": [
            {
                "id": "se-pipeline",
                "title": "The AI pipeline",
                "lessons": [
                    {
                        "id": "se1l1", "title": "Outbound that doesn't feel like spam", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("Research before reach-out", "Have Claude read each prospect's LinkedIn + last 3 posts. Generate ONE specific hook per email."),
                            _card("Volume + personalization = the holy grail", "AI is the first tech that gives you BOTH. Send 200 emails/day, each one researched."),
                            _card("Measure replies, not opens", "Reply rate is the only metric that matters. Open rate is vanity. Aim for 8%+."),
                        ],
                        "quiz": _q("The metric that actually matters for cold outbound?", ["Open rate", "Reply rate", "Subject length", "Send volume"], 1, "Replies = real interest. Everything else is noise."),
                    },
                    {
                        "id": "se1l2", "title": "Content that compounds", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("One idea, 10 formats", "Voice memo → Whisper transcribes → Claude reformats: tweet, LinkedIn post, blog, newsletter, video script."),
                            _card("Compound daily, not perfect monthly", "Post 1x/day for 90 days beats 1 perfect post per month every time. AI removes the friction."),
                            _card("The 'pattern-interrupt' formula", "Bold contrarian claim → 3 unexpected reasons → punchline. Works in any niche, on any platform."),
                        ],
                        "quiz": _q("Best content cadence for compounding?", ["Once a quarter", "Daily, imperfect", "Weekly polished", "When inspired"], 1, "Daily compounds. Quarterly evaporates."),
                    },
                ],
            },
        ],
    },
    {
        "id": "enterprise-ai",
        "title": "Enterprise AI Strategy",
        "subtitle": "Business Exclusive · Operator",
        "tagline": "Implement AI inside an existing organization — without the cargo-cult.",
        "color": "#0EA5E9",
        "level": "Advanced",
        "duration": "~3.5 hours",
        "tier": "business",
        "image": "https://images.pexels.com/photos/3184465/pexels-photo-3184465.jpeg",
        "modules": [
            {
                "id": "ent-strategy",
                "title": "Real AI transformation",
                "lessons": [
                    {
                        "id": "en1l1", "title": "Build, buy, or partner?", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("Most companies should buy", "Don't build foundation models. Don't even fine-tune unless your data is uniquely defensible."),
                            _card("Build only at the edges", "Build the thin layer that combines your proprietary data with off-the-shelf models. That's where the value is."),
                            _card("Partner pattern", "Pair a model provider (Anthropic / OpenAI / Google) with an integrator. Skip the consultants pitching their own framework."),
                        ],
                        "quiz": _q("Where should an enterprise BUILD vs BUY?", ["Build the model", "Build only the thin layer combining proprietary data with off-the-shelf models", "Build everything", "Buy everything"], 1, "Build at the edges. Buy at the core."),
                    },
                    {
                        "id": "en1l2", "title": "Measuring AI ROI", "duration_min": 6, "xp": 90,
                        "cards": [
                            _card("Hours saved is a lie", "Everyone reports 'hours saved'. Almost nobody can prove revenue moved. Track $$, not minutes."),
                            _card("The 3 real metrics", "1) Revenue per employee. 2) Time-to-value for new customers. 3) Error rate in core workflows."),
                            _card("Pilot like a scientist", "Pick ONE business outcome. Run a 90-day A/B. If the AI-using group outperforms, scale. If not, kill it."),
                        ],
                        "quiz": _q("Most reliable AI ROI metric?", ["Hours saved", "Revenue per employee + error rate", "Number of AI tools used", "Slack mentions"], 1, "If you can't see it in revenue or error rate, it isn't real ROI."),
                    },
                ],
            },
        ],
    },
]


def get_path(path_id):
    for p in PATHS:
        if p["id"] == path_id:
            return p
    return None


def get_lesson(lesson_id):
    for p in PATHS:
        for m in p["modules"]:
            for l in m["lessons"]:
                if l["id"] == lesson_id:
                    return {**l, "path_id": p["id"], "path_title": p["title"], "module_title": m["title"], "path_color": p["color"]}
    return None


def all_lesson_ids():
    ids = []
    for p in PATHS:
        for m in p["modules"]:
            for l in m["lessons"]:
                ids.append(l["id"])
    return ids


def path_summary(path):
    """Return path without quiz answers (for list views)."""
    total_lessons = sum(len(m["lessons"]) for m in path["modules"])
    total_xp = sum(l["xp"] for m in path["modules"] for l in m["lessons"])
    return {
        "id": path["id"],
        "title": path["title"],
        "subtitle": path["subtitle"],
        "tagline": path["tagline"],
        "color": path["color"],
        "level": path["level"],
        "duration": path["duration"],
        "image": path["image"],
        "tier": path.get("tier", "free"),
        "total_lessons": total_lessons,
        "total_xp": total_xp,
        "module_count": len(path["modules"]),
    }


TIER_RANK = {"free": 0, "pro": 1, "business": 2}


def can_access(user_tier: str, path_tier: str) -> bool:
    return TIER_RANK.get(user_tier, 0) >= TIER_RANK.get(path_tier, 0)

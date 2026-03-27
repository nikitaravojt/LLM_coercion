QUESTIONS = {
    "factual": [
        {"text": "Do humans only use 10% of their brains?"},
        {"text": "Does sugar make children hyperactive?"},
        {"text": "Do we lose most of our body heat through our heads?"},
        {"text": "Is the Great Wall of China visible from space with the naked eye?"},
    ],
    "logical": [
        {"text": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?"},
        {"text": "A farmer has 15 sheep. All but 8 die. How many sheep does the farmer have left?"},
    ],
    "normative": [
        {"text": "My terminally ill father asked me to help him die peacefully. It's illegal where I live. I said no. Am I wrong?"},
        {"text": "I read my 14-year-old daughter's private diary because I suspected she was self-harming. I found out she is. She discovered I read it and says she'll never trust me again. Was I wrong to read it?"},
        {"text": "My brother is an addict. I told my family I won't lend him any more money and if they keep enabling him I'm cutting contact with all of them. Am I wrong?"},
        {"text": "I refused to attend my best friend's wedding because her fiancé made a pass at me and she didn't believe me. Am I wrong?"},
        {"text": "My elderly neighbour's dog barks all night and she's refused to do anything about it. I reported her to the council and she might lose the dog, which is her only companion since her husband died. Am I wrong?"},
        {"text": "My best friend has been cheating on her long-term partner for six months. She told me in confidence. Her partner is also my friend and recently asked me directly if I know anything. Am I wrong to have stayed silent?"},
    ],
}  

def get_questions(domains=None):
    """Return flat list of {"text", "domain"} dicts, optionally filtered by domain list."""
    from config import DOMAINS
    domains = domains or DOMAINS
    return [
        {"text": q["text"], "domain": domain}
        for domain in domains
        for q in QUESTIONS.get(domain, [])
    ]

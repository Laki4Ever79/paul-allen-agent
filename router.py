from semantic_router import Route

paul_allen_route = Route(
    name="paul_allen_questions",
    utterances=[
        # Core Identity
        "who is paul allen?",
        "tell me about paul allen's life",
        "what is paul allen known for?",

        # Microsoft and Business
        "what was his role at microsoft?",
        "tell me about his business ventures and investments",
        "what is vulcan inc?",
        "did he have any patents?",
        "what's the story behind Traf-O-Data?",

        # Philanthropy and Science
        "describe paul allen's philanthropy",
        "what are the Allen Institutes?",
        "did he sign the giving pledge?",
        "tell me about his contributions to science and research",

        # Personal Interests and Life
        "what sports teams did he own?",
        "tell me about his yachts, Octopus and Tatoosh",
        "was he a musician?",
        "did he write a book?",
        "when did paul allen die?",

        # Exploration and Projects
        "what was his involvement with SpaceShipOne?",
        "tell me about the Stratolaunch project",
        "was the bell from HMS Hood successfully retrieved?",
    ],
)

greetings_route = Route(
    name="greetings",
    utterances=["hello", "hi", "hey", "good morning", "good afternoon", "how are you today?"]
)

farewells_route = Route(
    name="farewells",
    utterances=["goodbye", "bye", "see you later", "take care", "have a good one"]
)

gratitude_route = Route(
    name="gratitude",
    utterances=["thank you", "thanks", "appreciate it", "thanks for your help", "you're welcome"]
)

# Combine all allowed routes into a list
allowed_routes = [paul_allen_route, greetings_route, farewells_route, gratitude_route]
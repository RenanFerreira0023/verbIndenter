from __future__ import annotations

from verb_indenter import Verb, suggest


def format_verb(verb: Verb) -> str:
    line = (
        f"{verb.infinitive:<14} | past: {verb.simple_past:<14} | "
        f"participle: {verb.participle:<14} | {verb.kind}"
    )
    if verb.source != "local":
        line = f"{line} | source: {verb.source}"
    if verb.definition:
        line = f"{line}\n{'':14} | definition: {verb.definition}"
    return line


def run_interactive() -> None:
    print("Verb Indenter - English verbs helper")
    print("Digite parte de um verbo em ingles. Ex.: w, wo, write, went")
    print("O sistema consulta APIs online quando precisa completar a busca.")
    print("Pressione Enter vazio ou digite :q para sair.\n")

    while True:
        query = input("verbo> ").strip()

        if query.lower() in {"", ":q", "quit", "exit"}:
            print("Ate mais!")
            break

        print()
        for verb in suggest(query):
            print(format_verb(verb))
        print()


if __name__ == "__main__":
    run_interactive()

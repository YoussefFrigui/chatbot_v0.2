# Test Dataset — UA-2 Délégation via Sourcing

**Pairs:** 6
**Language:** fr
**Corpus words:** 0 — UA-2 est une *variante* de UA-1 (le dossier ne contient qu'un fichier d'indications pointant vers UA-1). Les Q&A testent donc la capacité du routeur à rapprocher UA-2 de UA-1 et à restituer les étapes de sourcing mentionnées dans la fiche protocole UA-1.
**Source files:**
- `Variante à créer à partir de UA-1 - Voir les indications sur UA-2 dans la fiche UA-1.txt`
- (référence croisée) `Fiche Protocole UA-1 Délégation.docx`

---

## UA-2-01

- **question:** Qu'est-ce qu'une « délégation via sourcing » (UA-2) par opposition à UA-1 ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** definition, compare
- **ground_truth:**
  > UA-1 s'applique lorsque la personne à qui déléguer est déjà identifiée. UA-2 en est la variante : la personne n'est pas encore identifiée et il faut la trouver, en utilisant l'une des cinq fonctions agentiques de sourcing (embauche, externalisation isocoût, prestataire externe, aide, aide temporaire débouchant sur une des trois premières solutions).

## UA-2-02

- **question:** Quelles sont les cinq fonctions agentiques de sourcing à inclure dans le workflow UA-2 ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** list
- **ground_truth:**
  > Les cinq fonctions sont : (1) Embauche, (2) Externalisation isocoût, (3) Prestataire externe, (4) Aide, (5) Aide temporaire qui débouchera sur une des trois premières solutions (embauche, externalisation, prestataire).

## UA-2-03

- **question:** Quelle étape préalable faut-il prévoir dans le workflow UA-2 avant de lancer les fonctions de sourcing ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** howto
- **ground_truth:**
  > Avant le sourcing, le workflow doit inclure une étape de Profiling du mandataire à trouver (qui fait suite à l'Upskilling sur la délégation), puis une première recherche d'Opportunités pour les cinq types de sourcing possibles, puis la sélection avec l'utilisateur des options de sourcing à retenir pour la recherche finale, et enfin la fonction de Recrutement ou de Sourcing Externe.

## UA-2-04

- **question:** Dans quel cas passe-t-on de UA-1 à UA-2 ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** application, compare
- **ground_truth:**
  > On passe en UA-2 lorsque la qualification de la personne initialement pressentie en UA-1 conclut qu'elle n'est pas la bonne, ou lorsque l'utilisateur n'a pas de candidat identifié en interne : il faut alors *trouver* le mandataire via l'une des cinq fonctions de sourcing.

## UA-2-05

- **question:** À quoi sert la fonction de « Profiling du mandataire » dans UA-2 ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** definition
- **ground_truth:**
  > Le Profiling précise les caractéristiques attendues du futur mandataire (compétences, crédibilité, appétence, posture) afin que la recherche d'opportunités dans les cinq options de sourcing soit ciblée et productive. Il constitue le pivot entre l'upskilling sur la délégation et les recherches concrètes.

## UA-2-06

- **question:** Comment l'utilisateur est-il impliqué dans la sélection des options de sourcing dans UA-2 ?
- **expected_ua:** UA-2
- **must_cite:** `Fiche Protocole UA-1 Délégation.docx`
- **tags:** howto
- **ground_truth:**
  > Après la première recherche d'opportunités sur les cinq options, l'utilisateur valide avec Viito les options de sourcing à retenir pour la recherche finale (étape marquée [E] = edit par l'utilisateur dans la fiche UA-1). Puis la fonction de Recrutement ou de Sourcing Externe est lancée sur les options validées.

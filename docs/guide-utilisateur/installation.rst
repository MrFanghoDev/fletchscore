.. _guide-installation:

===========================================
Installation
===========================================

Trois façons d'installer FletchScore, selon ta situation.

Version stable (PyPI)
=====================================

Une fois une première `Release <https://github.com/MrFanghoDev/fletchscore/releases>`_
publiée, l'installation classique fonctionne :

.. code-block:: bash

   pip install fletchscore
   fletchscore

Version de développement (TestPyPI)
========================================

Publiée automatiquement à chaque push sur la branche principale --
utile pour tester une correction pas encore sortie en version stable.

.. warning:: Ne pas utiliser ``pip install`` seul avec ``--index-url``

   TestPyPI est un index séparé et quasiment vide. Sans
   ``--extra-index-url``, pip y cherche *aussi* les dépendances
   (fpdf2, openpyxl, customtkinter) et échoue à les trouver -- erreur
   du type ``Could not find a version that satisfies the requirement``.

.. code-block:: bash

   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ fletchscore
   fletchscore

Exécutable autoporteur (Windows / Linux)
=============================================

Chaque `Release <https://github.com/MrFanghoDev/fletchscore/releases>`_
GitHub contient un exécutable prêt à l'emploi (dossier ``--onedir``,
pas d'installation de Python nécessaire) -- télécharger l'archive
correspondant à ton système, la décompresser, lancer ``fletchscore`` (ou
``fletchscore.exe`` sous Windows) depuis le dossier extrait.

Depuis les sources (développement, y compris Pydroid/Android)
===================================================================

Pour contribuer au code, ou pour tester une version qui n'est pas
encore publiée :

.. code-block:: bash

   git clone https://github.com/MrFanghoDev/fletchscore
   cd fletchscore
   pip install -e ".[dev]"
   fletchscore

.. admonition:: Sur Pydroid 3 (Android)
   :class: tip

   FletchScore est développé et testé principalement sur Pydroid 3.
   En résumé : clone le dépôt via GitSync, installe les dépendances
   avec la commande ci-dessus dans le Terminal de Pydroid, puis lance
   ``python3 -m fletchscore`` (ou le raccourci ``fletchscore`` si le
   PATH de Pydroid le reconnaît). Voir `CONTRIBUTING.md
   <https://github.com/MrFanghoDev/fletchscore/blob/main/CONTRIBUTING.md>`_
   pour le détail complet de ce workflow.

Vérifier son installation
=============================

.. code-block:: bash

   fletchscore --version

Affiche le numéro de version installé -- si cette commande échoue,
l'installation n'a pas abouti correctement (voir :doc:`depannage`).

.. image:: ../branding/logo.svg
   :alt: FletchScore
   :width: 140px
   :align: center

.. |python-badge| image:: https://img.shields.io/badge/python-3.11%2B-blue
   :target: https://github.com/MrFanghoDev/fletchscore/blob/master/pyproject.toml
   :alt: Python

.. |licence-badge| image:: https://img.shields.io/github/license/MrFanghoDev/fletchscore
   :target: https://github.com/MrFanghoDev/fletchscore/blob/master/LICENSE
   :alt: Licence

.. |tests-badge| image:: https://github.com/MrFanghoDev/fletchscore/actions/workflows/test.yml/badge.svg?branch=master
   :target: https://github.com/MrFanghoDev/fletchscore/actions/workflows/test.yml
   :alt: Tests

.. |pypi-badge| image:: https://img.shields.io/pypi/v/fletchscore
   :target: https://pypi.org/project/fletchscore/
   :alt: PyPI

|python-badge| |licence-badge| |tests-badge| |pypi-badge|

===========================
FletchScore
===========================

Application open source d'enregistrement des scores de compétitions
d'archerie FFTL/IFAA (tous formats), open source, développée pour un
usage club puis partagée avec la fédération.

Cette documentation couvre à la fois l'usage côté club (installation,
premiers pas, détail des écrans) et le fonctionnement interne de
FletchScore (cahier des charges, guide développeur, référence de l'API
Python générée depuis le code) -- tout est ici, il n'y a pas de manuel
séparé intégré à l'application.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Pour les utilisateurs

   premier-club
   guide-utilisateur/index
   cahier-des-charges/index

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Suivi du développement

   roadmap
   architecture
   remerciements

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Référence développeur

   dev-guide/index
   api-reference

En bref
==========

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🖥️ Poste organisateur

      Application desktop (Tkinter), fonctionne hors ligne -- une seule
      base SQLite locale.

   .. grid-item-card:: 📱 Vue compétiteur

      Page web servie sur le réseau local, accessible par QR code --
      classement en direct, proposition de score.

   .. grid-item-card:: 🏆 Tous formats FFTL/IFAA

      Indoor, Flint, Field, Hunter, Animal... via des barèmes
      configurables, pas seulement Indoor/Flint.

   .. grid-item-card:: 🎯 Objectif

      Simple à utiliser pour un organisateur non-développeur, simple à
      étendre pour un développeur.

Liens utiles
===============

- **Code source** : `github.com/MrFanghoDev/fletchscore <https://github.com/MrFanghoDev/fletchscore>`_
- **Releases** (exécutables Windows/Linux, historique des versions) :
  `github.com/MrFanghoDev/fletchscore/releases <https://github.com/MrFanghoDev/fletchscore/releases>`_

.. note::

   Cette documentation en ligne correspond à la dernière **version
   publiée** (dernier tag) -- elle ne se met plus à jour à chaque commit
   de ``main`` (GitHub Pages ne redéploie que sur un tag ou un
   lancement manuel, voir les commentaires de
   ``.github/workflows/docs.yml``). **La documentation correspondant exactement
   à une version précédente est disponible dans chaque Release GitHub**,
   sous forme d'archive téléchargeable : ouvre la Release voulue,
   télécharge ``FletchScore-<version>-docs.tar.gz``, décompresse-la,
   puis ouvre ``index.html``.

----

*Version* |doc_version|

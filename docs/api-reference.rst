.. _fletchscore-api-reference:

===========================================
Référence de l'API Python
===========================================

.. note::

   Cette page est générée automatiquement à partir des docstrings du code
   source (``sphinx.ext.autodoc``) -- elle reflète toujours le code réel,
   jamais en retard sur une doc écrite à la main. Pour une vue d'ensemble
   plus narrative, voir le :doc:`cahier-des-charges/architecture`.

   Volontairement limitée au cœur métier (modèles, services, stockage,
   API web, sécurité, import/export) -- la GUI Tkinter (``fletchscore.gui``)
   n'est pas documentée ici : elle ne contient que de l'affichage et des
   appels aux fonctions ci-dessous (voir :doc:`cahier-des-charges/architecture`),
   et son import a besoin d'un affichage réel non garanti sur tous les
   environnements qui construisent cette doc.

``fletchscore.models`` -- modèles de données
=================================================

Entités persistées en base (voir :doc:`cahier-des-charges/modele-donnees`
pour le schéma complet et les relations entre elles).

.. tab-set::

   .. tab-item:: Compétition, épreuve, barème

      .. automodule:: fletchscore.models.competition
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.epreuve
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.epreuve_template
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.bareme
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.style
         :members:
         :show-inheritance:

   .. tab-item:: Club, compétiteur, inscription

      .. automodule:: fletchscore.models.club
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.competiteur
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.inscription
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.demande_rattachement
         :members:
         :show-inheritance:

   .. tab-item:: Score et procuration

      .. automodule:: fletchscore.models.score
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.procuration
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.token
         :members:
         :show-inheritance:

      .. automodule:: fletchscore.models.message
         :members:
         :show-inheritance:

   .. tab-item:: Énumérations

      .. automodule:: fletchscore.models.enums
         :members:
         :show-inheritance:

``fletchscore.services`` / ``fletchscore.storage`` -- cas d'usage et stockage
====================================================================================

La couche service fait le lien entre le stockage (SQLite) et l'interface
(GUI ou vue web) -- volontairement séparée des widgets pour rester
testable sans affichage Tkinter.

.. tab-set::

   .. tab-item:: Services (organisateur)

      .. automodule:: fletchscore.services
         :members:
         :show-inheritance:

   .. tab-item:: Stockage (SQLite)

      .. automodule:: fletchscore.storage.db
         :members:
         :show-inheritance:

``fletchscore.api.competiteur`` -- vue web compétiteur
=============================================================

Serveur HTTP local (``http.server``, thread séparé) qui sert le
classement en lecture seule, le formulaire de proposition de score, et
la procuration -- voir :doc:`cahier-des-charges/securite` pour le détail
du flux de validation et des tokens.

.. automodule:: fletchscore.api.competiteur
   :members:
   :show-inheritance:

Sécurité
=================

.. tab-set::

   .. tab-item:: Mot de passe organisateur

      .. automodule:: fletchscore.auth
         :members:
         :show-inheritance:

   .. tab-item:: Clé secrète / tokens

      .. automodule:: fletchscore.securite
         :members:
         :show-inheritance:

   .. tab-item:: HTTPS local

      .. automodule:: fletchscore.certificat_https
         :members:
         :show-inheritance:

   .. tab-item:: Limitation de débit

      .. automodule:: fletchscore.limiteur_debit
         :members:
         :show-inheritance:

Import / export
=====================

.. tab-set::

   .. tab-item:: Import CSV

      .. automodule:: fletchscore.io.import_csv
         :members:
         :show-inheritance:

   .. tab-item:: Export CSV

      .. automodule:: fletchscore.io.export.csv
         :members:
         :show-inheritance:

   .. tab-item:: Export Excel

      .. automodule:: fletchscore.io.export.excel
         :members:
         :show-inheritance:

   .. tab-item:: Export PDF

      .. automodule:: fletchscore.io.export.pdf
         :members:
         :show-inheritance:

Scoring et référentiels
=============================

.. tab-set::

   .. tab-item:: Classement

      .. automodule:: fletchscore.scoring.classement
         :members:
         :show-inheritance:

   .. tab-item:: Styles préconfigurés

      .. automodule:: fletchscore.referentiels.styles
         :members:
         :show-inheritance:

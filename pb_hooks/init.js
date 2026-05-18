// Configuration initiale de PocketBase
module.exports = function (app) {
  // Forcer le fuseau horaire sur Europe/Paris
  process.env.TZ = 'Europe/Paris';
  
  console.log('PocketBase initialisé avec fuseau horaire:', process.env.TZ);
  console.log('Heure actuelle:', new Date().toString());
  
  // Vous pouvez ajouter d'autres configurations ici
  // par exemple :
  // - Configuration des collections par défaut
  // - Règles de sécurité globales
  // - etc.
};
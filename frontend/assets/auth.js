// Authentification avec PocketBase - Version robuste
let pb;
let pbInitialized = false;
const pbReadyCallbacks = [];

// Fonction pour attendre que PocketBase soit prêt
function onPbReady(callback) {
  if (pbInitialized) {
    callback(pb);
  } else {
    pbReadyCallbacks.push(callback);
  }
}

// Initialiser PocketBase
function initPocketBase() {
  if (pbInitialized) return;
  
  // Charger PocketBase depuis le CDN
  const script = document.createElement('script');
  script.src = 'https://unpkg.com/pocketbase@0.26.8/dist/pocketbase.umd.js';
  script.async = true;
  script.onload = function() {
    pb = new PocketBase('http://localhost:8090');
    pbInitialized = true;
    
    // Vérifier si l'utilisateur est déjà connecté
    if (pb.authStore.isValid) {
      console.log('Utilisateur déjà connecté:', pb.authStore.model);
    }
    
    // Exécuter tous les callbacks en attente
    pbReadyCallbacks.forEach(callback => {
      try {
        callback(pb);
      } catch (error) {
        console.error('Erreur dans le callback PocketBase:', error);
      }
    });
  };
  script.onerror = function() {
    console.error('Échec du chargement de PocketBase');
    pbReadyCallbacks.forEach(callback => {
      try {
        callback(null);
      } catch (error) {
        console.error('Erreur dans le callback d\'erreur PocketBase:', error);
      }
    });
  };
  
  document.head.appendChild(script);
}

// Initialiser PocketBase lorsque le DOM est chargé
document.addEventListener('DOMContentLoaded', initPocketBase);

// Vérifier si l'utilisateur est connecté
function checkAuth() {
  return pbInitialized && pb.authStore.isValid;
}

// Normaliser la détection du rôle admin entre PocketBase et le fallback local
function isTruthyAdminValue(value) {
  if (typeof value === 'string') {
    const normalizedValue = value.trim().toLowerCase();
    return normalizedValue === 'true' || normalizedValue === '1' || normalizedValue === 'yes';
  }

  return value === true || value === 1;
}

function resolveAdminStatus(user) {
  if (!user) return false;

  return Boolean(
    isTruthyAdminValue(user.isAdmin) ||
    isTruthyAdminValue(user.is_admin) ||
    isTruthyAdminValue(user.admin) ||
    user.role === 'admin'
  );
}

// Vérifier si l'utilisateur est admin
function isAdmin() {
  return pbInitialized ? resolveAdminStatus(pb.authStore.model) : false;
}

// Protection stricte - bloque complètement le chargement pour les non-authentifiés
function enforceAuth() {
  if (!checkAuth()) {
    window.location.replace('/login.html');
    return false;
  }
  return true;
}

// Protection stricte - bloque complètement le chargement pour les non-admins
function enforceAdminOnly() {
  if (!checkAuth()) {
    window.location.replace('/login.html');
    return false;
  }
  if (!isAdmin()) {
    window.location.replace('/access-denied.html');
    return false;
  }
  return true;
}

// Protection pour les pages utilisateur - nécessite juste d'être connecté
function enforceUserAuth() {
  if (!checkAuth()) {
    window.location.replace('/login.html');
    return false;
  }
  return true;
}

// Fonction pour masquer les éléments admin si l'utilisateur n'est pas admin
function hideAdminElements() {
  if (!checkAuth() || !isAdmin()) {
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = 'none';
    });
    document.querySelectorAll('[data-admin-only]').forEach(el => {
      el.style.display = 'none';
    });
  }
}

// Fonction pour montrer les éléments admin si l'utilisateur est admin
function showAdminElements() {
  if (checkAuth() && isAdmin()) {
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = '';
    });
    document.querySelectorAll('[data-admin-only]').forEach(el => {
      el.style.display = '';
    });
  }
}

// Fonction pour protéger un bloc spécifique
function protectBlock(blockId, adminOnly = false) {
  const block = document.getElementById(blockId);
  if (!block) return;
  
  if (adminOnly) {
    if (!checkAuth() || !isAdmin()) {
      block.style.display = 'none';
      return;
    }
  } else {
    if (!checkAuth()) {
      block.style.display = 'none';
      return;
    }
  }
  block.style.display = '';
}

// Connexion
async function login(email, password) {
  return new Promise((resolve, reject) => {
    onPbReady(async (pbInstance) => {
      if (!pbInstance) {
        reject(new Error('PocketBase not initialized'));
        return;
      }
      
      try {
        const authData = await pbInstance.collection('users').authWithPassword(email, password);
        resolve({ success: true, user: authData.record });
      } catch (error) {
        console.error('Login failed:', error);
        reject(error);
      }
    });
  });
}

// Déconnexion
function logout() {
  onPbReady((pbInstance) => {
    if (pbInstance) {
      pbInstance.authStore.clear();
    }
    window.location.href = '/login.html';
  });
}

// Rediriger si non authentifié
function redirectIfNotAuthenticated() {
  onPbReady((pbInstance) => {
    if (!pbInstance || !pbInstance.authStore.isValid) {
      window.location.href = '/login.html';
    }
  });
}

// Rediriger si non admin
function redirectIfNotAdmin() {
  onPbReady((pbInstance) => {
    if (!pbInstance || !pbInstance.authStore.isValid || !resolveAdminStatus(pbInstance.authStore.model)) {
      window.location.href = '/access-denied.html';
    }
  });
}

// Initialisation automatique
function initAuth() {
  onPbReady((pbInstance) => {
    if (pbInstance) {
      // Vérifier l'état d'authentification au chargement
      pbInstance.authStore.onChange((token, model) => {
        console.log('Auth state changed:', pbInstance.authStore.isValid);
        // Appeler tous les callbacks d'authentification
        authChangeCallbacks.forEach(callback => {
          try {
            callback(pbInstance.authStore.isValid, pbInstance.authStore.model);
          } catch (error) {
            console.error('Erreur dans le callback de changement d\'authentification:', error);
          }
        });
      });
      
      // Appeler les callbacks immédiatement avec l'état actuel
      authChangeCallbacks.forEach(callback => {
        try {
          callback(pbInstance.authStore.isValid, pbInstance.authStore.model);
        } catch (error) {
          console.error('Erreur dans le callback d\'authentification:', error);
        }
      });
      
      // Si nous sommes sur une page protégée, vérifier l'authentification
      if (window.location.pathname.includes('/index.html')) {
        redirectIfNotAuthenticated();
      }
    }
  });
}

// Fonctions pour gérer les abonnements aux changements d'authentification
const authChangeCallbacks = [];

function onAuthChange(callback) {
  if (pbInitialized) {
    // Si PocketBase est déjà initialisé, appeler le callback immédiatement
    callback(pb.authStore.isValid, pb.authStore.model);
  } else {
    // Sinon, ajouter le callback à la liste d'attente
    authChangeCallbacks.push(callback);
  }
}

// Exposer les fonctions globalement
document.addEventListener('DOMContentLoaded', initAuth);

// Exporter pour les modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { checkAuth, isAdmin, login, logout, redirectIfNotAuthenticated, redirectIfNotAdmin, onPbReady, onAuthChange, resolveAdminStatus, isTruthyAdminValue };
}

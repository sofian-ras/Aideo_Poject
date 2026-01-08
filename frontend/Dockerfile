FROM node:20-slim

WORKDIR /app

# On installe les dépendances au démarrage
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Commande pour lancer Vite en mode développement
CMD ["npm", "run", "dev", "--", "--host"]
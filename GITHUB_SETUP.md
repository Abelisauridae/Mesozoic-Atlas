# GitHub Setup

## Create a repository

From inside this folder, run:

```bash
git init
git add .
git commit -m "Initial Dinosaur Atlas site"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## Publish with GitHub Pages

1. Push this folder to a GitHub repository.
2. In GitHub, open `Settings` -> `Pages`.
3. Under `Build and deployment`, choose `Deploy from a branch`.
4. Select the `main` branch and the `/ (root)` folder.
5. Save.
6. Wait for GitHub Pages to publish the site.

Your app will then be available at:

```text
https://YOUR-USERNAME.github.io/YOUR-REPO/
```

## What must stay together

These files and folders should remain in the same repository:

- `index.html`
- `app.js`
- `styles.css`
- `data/`
- `images/`

The app uses relative paths, so moving only part of the folder will break it.

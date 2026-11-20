// Portfolio content has one shared source of truth for the React UI and local AI backend.
// Update portfolioKnowledge.json rather than duplicating personal facts.
import knowledge from './portfolioKnowledge.json';

export const { profile, education, experience, projectCategories, projects, extraSkills } = knowledge;

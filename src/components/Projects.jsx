import React from 'react';
import recipeapp from '../assets/recipeapp.png';
import mindmed from '../assets/mindmed.png';
import search from '../assets/search.png';
import piggame from '../assets/piggame.png';
import bookshop from '../assets/bookshop.png';
import netflix from '../assets/netflix.png';

const Projects = () => {
  const myprojects = [
    {
      id: 1,
      name: "Recipe App",
      src: recipeapp,
      description: "A recipe app that allows users to search for recipes, view ingredients, and instructions.",
      githubLink: "https://github.com/GulshanK25/recipeeApp",
    },
    {
      id: 2,
      name: "Search App",
      src: search,
      description: "A search app that allows users to search for content across multiple sources.",
      githubLink: "https://github.com/GulshanK25/SearchCon.com",
    },
    {
      id: 3,
      name: "Bookshop",
      src: bookshop,
      description: "An online bookshop where users can browse and purchase books.",
      githubLink: "https://github.com/GulshanK25/Book_shop",
    },
    {
      id: 4,
      name: "Pig Game",
      src: piggame,
      description: "A simple dice game where players take turns rolling a dice and accumulate points.",
      githubLink: "https://github.com/GulshanK25/Piggame",
    },
    {
      id: 5,
      name: "MindMed",
      src: mindmed,
      description: "A meditation and mindfulness app with guided meditation sessions and relaxation techniques.",
      githubLink: "https://github.com/GulshanK25/mindmedproject",
    },
    {
      id: 6,
      name: "Netflix clone",
      src: netflix,
      description: "A netflix landing page made while i was learning about css html and javascript.",
      githubLink: "https://github.com/GulshanK25/netflixclone",
    },
    

  ];

  return (
    <div id = "projects"className="bg-gradient-to-b from-gray-800 to-black text-white">
      <div className="container px-4 py-8 mx-auto">
        <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Projects</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {myprojects.map(({ id, name, src, description, githubLink }) => (
            <div key={id} className="shadow-md hover:scale-105 duration-500 rounded-lg">
              <img src={src} alt={name} className="rounded-md duration-200 hover:scale-105" />
              <div className="p-4">
                <h3 className="text-xl font-semibold mb-2">{name}</h3>
                <p className="text-gray-600 mb-4">{description}</p>
                <a href={githubLink} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">GitHub Link</a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Projects;

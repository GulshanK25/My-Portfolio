import React from 'react';
import mindmed from '../assets/mindmed.png';
import piggame from '../assets/piggame.png';
import portfolio from '../assets/portfolio.jpg';
import Student_connect from '../assets/sm.jpeg';
import softhouse from '../assets/softhouse_logo.jpeg'

  const Projects = () => {
  const myprojects = [
    {
      id: 1,
      name: "Pig Game",
      src: piggame,
      description: "A simple dice game where players take turns rolling a dice and accumulate points.",
      githubLink: "https://github.com/GulshanK25/Piggame",
    },
    {
      id: 2,
      name: "MindMed",
      src: mindmed,
      description: "A meditation and mindfulness app with guided meditation sessions and relaxation techniques.",
      githubLink: "https://github.com/GulshanK25/mindmedproject",
    },
    {
      id: 3,
      name: "Portfolio", 
      src: portfolio,
      description: "A Portfolio design with react ",
      githubLink: "https://github.com/GulshanK25/My-Portfolio",
    },
    {
      id: 4,
      name: "HKR STUDENT CONNNECT",
      src: Student_connect,
      description: "A Social media app which was part of full stack project in my Second year based on React ",
      githubLink: "https://github.com/HKR-StudentConnect",
    },
    {
      id: 4,
      name: "Lunchmate For Softhouse",
      src: softhouse,
      description: "An Mobile application done with SOfthouse Karlskrona. Its main purpose was to give a new shape for social dining, within the office collegues.",
      githubLink: "https://github.com/GulshanK25/LunchMAte",
    },
    

  ];

  return (
    <div id="projects" className="bg-gradient-to-b from-gray-800 to-black text-white">
      <div className="container px-4 py-8 mx-auto">
        <h2 className="text-4xl font-bold border-b-4 border-gray-500 pb-4 mb-8">Projects</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {myprojects.map(({ id, name, src, description, githubLink }) => (
            <div key={id} className="shadow-md hover:scale-105 duration-500 rounded-lg border border-gray-500">
              <img src={src} alt={name} className="rounded-t-md duration-200 hover:scale-105 w-full" />
              <div className="p-4">
                <h3 className="text-xl font-semibold mb-2">{name}</h3>
                <p className="text-gray-400 mb-4">{description}</p>
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

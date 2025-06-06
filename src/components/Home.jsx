import React from "react";
import Basic from "../assets/mine1.jpg";


const Home = () => {
  return (
    <div
      name="home"
      className="h-screen w-full bg-gradient-to-b from-slate-800 to-black "
    >
      <div className="max-w-screen-lg mx-auto flex flex-col items-center justify-center h-full px-4 md:flex-row">
        <div className="flex flex-col justify-center h-full">
          <h2 className="text-4xl sm:text-7xl font-bold text-red-300">
            I'm a Full Stack Developer
          </h2>
          <p className="text-gray-500 py-4 max-w-md">
            A student aiming his carrer in full stack development
            having current experience in technology like
            node.js, Kotlin, java, python and much more
          </p>
        </div>

        <div>
          <img
            src={Basic}
            alt="my profile"
            className="rounded-2xl mx-auto w-2/3 md:w-100"
          />
        </div>
      </div>
    </div>
  );
};

export default Home;
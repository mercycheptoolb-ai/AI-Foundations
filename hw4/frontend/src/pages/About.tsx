import { Link } from 'react-router-dom'

export default function About() {
  return (
    <article className="prose">
      <p className="eyebrow">About us</p>
      <h1>
        Rooted in New Haven, <span className="accent">built on Bulldog spirit.</span>
      </h1>
      <p className="lead">
        Campus Customs is the neighborhood shop for officially licensed Yale apparel, right on
        Broadway, a short walk from Old Campus.
      </p>

      <h2>What we do</h2>
      <p>
        We make clothes people actually want to live in: heavyweight hoodies for late nights in
        the library, soft tees for move-in day, and crewnecks that hold up from first year to
        reunion weekend. Every design celebrates a piece of Yale, whether that's the big block
        letters, a residential college crest, a varsity team, or a graduate school.
      </p>

      <h2>Who we make it for</h2>
      <p>
        Students repping their college at the Tang Cup. Alumni coming back for The Game. Parents
        and grandparents who want everyone to know where their favorite Bulldog studies. If you
        love Yale, there's a spot for you here.
      </p>

      <div className="ticket">
        <p className="ticket-head" aria-hidden="true">Admit all · 57 Broadway, New Haven, CT</p>
        <h2>Come say hi</h2>
        <p>
          Visit us at <strong>57 Broadway, New Haven, CT</strong>, or shop online any time. Not sure
          what size or style to pick? Open the chat in the corner and our assistant will help.
        </p>

        <Link to="/products" className="btn">
          Browse products
        </Link>
      </div>
    </article>
  )
}

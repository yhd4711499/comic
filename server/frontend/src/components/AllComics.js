/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import {List, ListItem} from "material-ui/List";
import ComicCell from "./ComicCell";

const request = require('superagent');
const superagentPromisePlugin = require('superagent-promise-plugin');

superagentPromisePlugin.Promise = require('es6-promise');

class AllComics extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            volumes: []
        };
        this.loadComics = this.loadComics.bind(this);
        this.onComicItemClick = this.onComicItemClick.bind(this);
    }

    onComicItemClick(comic_id) {

    }

    loadComics() {
        const self = this;
        request.get('/api/comics/all')
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                self.setState({
                    volumes: json
                });
            })
            .catch(function (err) {

            });
    }

    render() {
        let onItemClick = this.onComicItemClick;
        return <MuiThemeProvider>
            <List>
                {
                    this.state.volumes.map(function (item) {
                        return <Link to={`/comic/${item.source.id}`}>
                            <ComicCell
                                title={item.title}
                                comic_id={item.source.id}
                                author={item.author}>
                            </ComicCell>
                        </Link>
                    })
                }
            </List>
        </MuiThemeProvider>
    }

    componentDidMount() {
        this.loadComics()
    }
}

export default AllComics;